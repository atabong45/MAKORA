#!/bin/bash
# MAKORA — Découverte des vrais endpoints et schémas POST
# Usage : bash scripts/discover_api.sh
# Nécessite que l'API soit lancée (docker compose up -d)

API="http://localhost:8000"

echo "=== TOUTES LES ROUTES ==="
curl -s $API/api/openapi.json | python3 -c "
import json,sys
spec = json.load(sys.stdin)
for path in sorted(spec['paths']):
    for method in spec['paths'][path]:
        if method in ('get','post','put','patch','delete'):
            print(f'{method.upper():7} {path}')
"

echo ""
echo "=== SCHÉMAS DES BODY POST (propriétés requises) ==="
curl -s $API/api/openapi.json | python3 -c "
import json,sys
spec = json.load(sys.stdin)
schemas = spec.get('components',{}).get('schemas',{})

for path in sorted(spec['paths']):
    for method in ('post','put','patch'):
        if method not in spec['paths'][path]: continue
        op = spec['paths'][path][method]
        body = op.get('requestBody',{})
        ref = body.get('content',{}).get('application/json',{}).get('schema',{}).get('\$ref','')
        if not ref: continue
        sname = ref.split('/')[-1]
        s = schemas.get(sname,{})
        required = s.get('required',[])
        props = list(s.get('properties',{}).keys())
        print(f'{method.upper()} {path}')
        print(f'  schema   : {sname}')
        print(f'  required : {required}')
        print(f'  all props: {props}')
        print()
"
