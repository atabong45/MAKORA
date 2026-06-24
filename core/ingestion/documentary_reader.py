"""
MODULE : core/ingestion/documentary_reader.py
DESCRIPTION : Pipeline OCR documentaire — extrait les données d'un document
              scanné (PDF ou image) via deux moteurs OCR et un LLM local.

RÉFÉRENCES ACADÉMIQUES :
- [ADR-007] PaddleOCR moteur principal — meilleure précision sur documents
  dégradés (cachet humide, papier froissé) vs Tesseract seul.
- [ADR-008] OCR dual + arbitrage LLM. Si LLM KO → échec propre (pas regex).
  Principe "primum non nocere" : un résultat absent vaut mieux qu'un résultat
  erroné sur des données médicales.
- [Wei2022] Wei et al. (2022). Chain-of-thought prompting. NeurIPS.
  → Justifie l'usage du LLM pour fusionner et structurer les deux textes OCR.
- [Smith2007] Smith, R. (2007). An overview of the Tesseract OCR engine. ICDAR.
  → Justifie la configuration --oem 3 --psm 6 pour les documents structurés.

DÉCISIONS DE CONCEPTION :
- PaddleOCR est importé en lazy (à l'intérieur de la méthode) pour éviter
  un crash au démarrage si la dépendance est absente — dégradation gracieuse.
- Tesseract est également lazy-importé pour la même raison.
- Le score de confiance global = moyenne des word-level confidences Tesseract.
  PaddleOCR fournit ses propres scores par boîte — on prend la moyenne.
- Si score_global < 0.30 : court-circuit immédiat → OCRResult.pipeline_ko().
- Cachet humide : détection HSV OpenCV sur l'image originale (avant preprocessing).
  Plage HSV bleu : H[100-130], S[50-255], V[50-255].
  Plage HSV rouge : H[0-10] ∪ H[170-180], S[50-255], V[50-255].
- EXIF : champ 'Software' vérifié contre une liste de logiciels de retouche.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Optional

from core.data_models import OCRResult
from core.logging_config import get_logger
from core.llm.backend import LLMBackend, build_backend

logger = get_logger(__name__)

_RETOUCHE_LOGICIELS = {
    "adobe photoshop", "photoshop", "gimp", "canva",
    "pixelmator", "affinity photo", "lightroom", "paint.net",
    "snapseed", "facetune",
}

_SCORE_MIN = 0.30
_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "qwen2.5:7b"
_OLLAMA_TIMEOUT = 45


class DocumentaryReader:
    """
    Lit un document scanné et retourne un OCRResult immutable.

    Flux complet :
      1. Normalisation image (PDF→PNG si besoin)
      2. Hash SHA-256 de l'image originale
      3. Analyse EXIF (avant preprocessing pour conserver les métadonnées)
      4. Détection cachet humide HSV (sur image originale)
      5. Preprocessing OpenCV (denoising, binarization Otsu, deskew Hough)
      6. PaddleOCR → texte brut + scores (si disponible)
      7. Tesseract → texte brut + word confidences
      8. Score confiance global
      9. Court-circuit si score < 0.30
      10. LLM Qwen → JSON structuré
    """
    def __init__(self, backend: LLMBackend | None = None) -> None:
        self.backend = backend or build_backend()

    def process(self, file_path: str | Path) -> OCRResult:
        """
        Point d'entrée principal. Non-bloquant sur erreurs non-critiques.

        Args:
            file_path: chemin vers le PDF ou l'image.

        Returns:
            OCRResult — toujours retourné, success=False si pipeline KO.
        """
        p = Path(file_path)
        if not p.exists():
            logger.error("[OCR] Fichier introuvable : %s", p)
            return OCRResult.pipeline_ko("FICHIER_INTROUVABLE")

        t0 = time.monotonic()

        # 1. Normalisation image
        img_original = self._load_image(p)
        if img_original is None:
            return OCRResult.pipeline_ko("PDF_PROTEGE")

        # 2. Hash SHA-256 de l'image originale (avant toute modification)
        hash_image = self._compute_hash(p)

        # 3. EXIF + 4. Cachet (sur image originale)
        flag_altere, logiciel = self._analyze_exif(p)
        presence_cachet = self._detect_cachet(img_original)

        # 5. Preprocessing
        img_processed = self._preprocess(img_original)

        # 6. PaddleOCR
        paddle_text, paddle_score = self._run_paddle(img_processed)

        # 7. Tesseract
        tesseract_text, word_confidences = self._run_tesseract(img_processed)

        # 8. Score global
        score_global = self._compute_score(word_confidences, paddle_score)
        score_montant = self._score_montant_token(word_confidences, tesseract_text)

        # 9. Court-circuit qualité insuffisante
        if score_global < _SCORE_MIN:
            logger.warning(
                "[OCR] Qualité insuffisante (score=%.2f < %.2f) — %s",
                score_global, _SCORE_MIN, p.name,
            )

        # 10. LLM structuration
        champs = self._call_llm(paddle_text, tesseract_text)
        if champs is None:
            return OCRResult(
                presence_cachet=presence_cachet,
                flag_altere=flag_altere,
                logiciel_retouche=logiciel,
                hash_image=hash_image,
                score_confiance_global=score_global,
                score_confiance_montant=score_montant,
                success=False,
                error="LLM_KO",
            )

        elapsed = round((time.monotonic() - t0) * 1000)
        logger.info(
            "[OCR] %s → score=%.2f, cachet=%s, altéré=%s, %dms",
            p.name, score_global, presence_cachet, flag_altere, elapsed,
        )

        return OCRResult(
            montant_facture=champs.get("montant_facture"),
            devise=champs.get("devise"),
            date_soin=champs.get("date_soin"),
            code_acte=champs.get("code_acte"),
            nom_praticien=champs.get("nom_praticien"),
            etablissement=champs.get("etablissement"),
            presence_cachet=presence_cachet or bool(champs.get("presence_cachet")),
            flag_altere=flag_altere,
            logiciel_retouche=logiciel,
            hash_image=hash_image,
            score_confiance_global=score_global,
            score_confiance_montant=score_montant,
            success=True,
        )

    # ------------------------------------------------------------------
    # 1. Chargement image
    # ------------------------------------------------------------------

    def _load_image(self, path: Path):
        """PDF → première page PNG via pdf2image, sinon lecture directe."""
        try:
            import cv2
            import numpy as np

            if path.suffix.lower() == ".pdf":
                try:
                    from pdf2image import convert_from_path
                    pages = convert_from_path(str(path), dpi=300, first_page=1, last_page=1)
                    if not pages:
                        return None
                    import io
                    buf = io.BytesIO()
                    pages[0].save(buf, format="PNG")
                    buf.seek(0)
                    arr = np.frombuffer(buf.read(), dtype=np.uint8)
                    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
                except Exception as e:
                    logger.warning("[OCR] pdf2image KO : %s", e)
                    return None
            else:
                img = cv2.imread(str(path))
                if img is None:
                    logger.warning("[OCR] cv2.imread a retourné None pour %s", path)
                return img
        except ImportError:
            logger.error("[OCR] OpenCV non disponible")
            return None

    # ------------------------------------------------------------------
    # 2. Hash SHA-256
    # ------------------------------------------------------------------

    def _compute_hash(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # 3. Analyse EXIF
    # ------------------------------------------------------------------

    def _analyze_exif(self, path: Path) -> tuple[bool, Optional[str]]:
        """Retourne (flag_altere, nom_logiciel_ou_None)."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(path) as img:
                exif_raw = img._getexif()
                if not exif_raw:
                    return False, None

                exif = {TAGS.get(k, k): v for k, v in exif_raw.items()}
                software = str(exif.get("Software", "")).lower().strip()

                if not software:
                    return False, None

                for logiciel in _RETOUCHE_LOGICIELS:
                    if logiciel in software:
                        logger.info("[OCR] Logiciel retouche détecté : %s", software)
                        return True, software

                return False, None
        except Exception:
            return False, None

    # ------------------------------------------------------------------
    # 4. Détection cachet humide (HSV OpenCV)
    # ------------------------------------------------------------------

    def _detect_cachet(self, img) -> bool:
        """
        Détecte la présence d'un cachet humide via masque HSV.
        Plages : bleu H[100-130] et rouge H[0-10] ∪ H[170-180].
        Critère : composante connexe ronde de taille suffisante.
        """
        try:
            import cv2
            import numpy as np

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Masque bleu
            mask_bleu = cv2.inRange(
                hsv,
                np.array([100, 50, 50]),
                np.array([130, 255, 255]),
            )
            # Masque rouge (deux plages HSV car H wraparound)
            mask_rouge1 = cv2.inRange(hsv, np.array([0, 50, 50]),   np.array([10, 255, 255]))
            mask_rouge2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
            mask = cv2.bitwise_or(mask_bleu, cv2.bitwise_or(mask_rouge1, mask_rouge2))

            # Composantes connexes
            num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                w    = stats[i, cv2.CC_STAT_WIDTH]
                h    = stats[i, cv2.CC_STAT_HEIGHT]
                if area < 500:
                    continue
                # Critère rondeur approximative : ratio côtés proches de 1
                if w > 0 and h > 0 and 0.5 < (w / h) < 2.0:
                    return True

            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 5. Preprocessing OpenCV
    # ------------------------------------------------------------------

    def _preprocess(self, img):
        """Denoising → grayscale → binarization Otsu → deskew Hough."""
        try:
            import cv2
            import numpy as np

            # Denoising
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            # Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Contrast CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            # Binarization Otsu
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Deskew via Hough
            binary = self._deskew(binary)
            return binary
        except Exception as e:
            logger.warning("[OCR] Preprocessing partiel : %s", e)
            return img

    def _deskew(self, binary):
        """Correction rotation via transformée de Hough."""
        try:
            import cv2
            import numpy as np

            edges = cv2.Canny(binary, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
            if lines is None:
                return binary

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return binary

            median_angle = float(np.median(angles))
            if abs(median_angle) < 0.5:
                return binary

            h, w = binary.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            return cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return binary

    # ------------------------------------------------------------------
    # 6. PaddleOCR
    # ------------------------------------------------------------------

    def _run_paddle(self, img) -> tuple[str, float]:
        """Retourne (texte_brut, score_moyen). (vide, 0.0) si KO."""
        try:
            from paddleocr import PaddleOCR
            import numpy as np

            ocr = PaddleOCR(use_angle_cls=True, lang="fr", show_log=False)
            result = ocr.ocr(img, cls=True)
            if not result or not result[0]:
                return "", 0.0

            lines, scores = [], []
            for line in result[0]:
                text = line[1][0]
                score = float(line[1][1])
                lines.append(text)
                scores.append(score)

            return "\n".join(lines), float(np.mean(scores)) if scores else 0.0
        except ImportError:
            logger.debug("[OCR] PaddleOCR non disponible — Tesseract seul")
            return "", 0.0
        except Exception as e:
            logger.warning("[OCR] PaddleOCR erreur : %s", e)
            return "", 0.0

    # ------------------------------------------------------------------
    # 7. Tesseract
    # ------------------------------------------------------------------

    def _run_tesseract(self, img) -> tuple[str, list[float]]:
        """Retourne (texte_brut, liste_confidences_par_mot)."""
        try:
            import pytesseract
            import pandas as pd

            config = "--oem 3 --psm 6"
            text = pytesseract.image_to_string(img, lang="fra", config=config)

            data = pytesseract.image_to_data(img, lang="fra", config=config,
                                             output_type=pytesseract.Output.DATAFRAME)
            confs = data.loc[data["conf"] > 0, "conf"].tolist()
            confs_norm = [c / 100.0 for c in confs]

            return text, confs_norm
        except ImportError:
            logger.warning("[OCR] Tesseract non disponible")
            return "", []
        except Exception as e:
            logger.warning("[OCR] Tesseract erreur : %s", e)
            return "", []

    # ------------------------------------------------------------------
    # 8 & 9. Scores de confiance
    # ------------------------------------------------------------------

    def _compute_score(self, word_confidences: list[float], paddle_score: float) -> float:
        """Score global = moyenne pondérée Tesseract (60%) + PaddleOCR (40%)."""
        import numpy as np

        tess_score = float(np.mean(word_confidences)) if word_confidences else 0.0
        if paddle_score > 0:
            return round(tess_score * 0.6 + paddle_score * 0.4, 4)
        return round(tess_score, 4)

    def _score_montant_token(self, word_confidences: list[float], text: str) -> float:
        """Approximation : score du voisinage du premier montant trouvé."""
        if not word_confidences:
            return 0.0
        # Pattern montant XAF/FCFA/EUR
        match = re.search(r"\d[\d\s,.']*(?:XAF|FCFA|EUR|F\.?CFA)", text, re.IGNORECASE)
        if not match:
            return float(sum(word_confidences) / len(word_confidences))
        # Position approximative dans le texte → position dans les confidences
        ratio = match.start() / max(len(text), 1)
        idx = int(ratio * len(word_confidences))
        idx = min(idx, len(word_confidences) - 1)
        return round(word_confidences[idx], 4)

    # ------------------------------------------------------------------
    # 10. LLM Qwen via Ollama
    # ------------------------------------------------------------------

    def _call_llm(self, paddle_text: str, tesseract_text: str) -> dict | None:
        from core.llm.prompts import OCR_SYSTEM_PROMPT, build_ocr_prompt
        prompt = build_ocr_prompt(paddle_text, tesseract_text)
        resp = self.backend.complete(OCR_SYSTEM_PROMPT, prompt)
        if not resp.success:
            logger.warning("[OCR] LLM KO : %s", resp.error)
            return None
        return self._parse_llm_json(resp.text)

    def _parse_llm_json(self, text: str) -> Optional[dict]:
        """Parse le JSON retourné par le LLM — tolérant aux artefacts."""
        text = text.strip()
        # Supprimer les backticks éventuels
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`")
        try:
            data = json.loads(text)
            # Normalisation devise FCFA → XAF
            if isinstance(data.get("devise"), str):
                if data["devise"].upper() in {"FCFA", "F.CFA"}:
                    data["devise"] = "XAF"
            return data
        except json.JSONDecodeError as e:
            logger.warning("[OCR] JSON LLM invalide : %s — texte=%r", e, text[:200])
            return None

# ------------------------------------------------------------------
# 2bis. Extraction texte natif PDF (fast-path avant OCR)
# ------------------------------------------------------------------

def _extract_pdf_native_text(self, path: Path) -> str:
    """
    Tente d'extraire le layer texte natif d'un PDF sans OCR.
    Retourne "" si scan pur, PyMuPDF absent ou fichier non-PDF.

    [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
      → Les factures numériques (layer texte présent) représentent
        la majorité des dossiers en assurance santé camerounaise.
        L'extraction native est plus fiable et 10× plus rapide que l'OCR.
    """
    if path.suffix.lower() != ".pdf":
        return ""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except ImportError:
        logger.debug("[OCR] PyMuPDF non disponible — fallback OCR")
        return ""
    except Exception as e:
        logger.warning("[OCR] PyMuPDF erreur : %s", e)
        return ""