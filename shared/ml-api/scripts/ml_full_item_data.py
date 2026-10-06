#!/usr/bin/env python3
"""
Obtiene todos los datos disponibles de un artículo de MercadoLibre.
Uso: python3 ml_full_item_data.py <ITEM_ID>
"""
import os, sys, json

# Add parent dir so ml_api import works from script dir
sys.path.insert(0, os.path.dirname(__file__))
from ml_api import read_credentials, get_token, api_get

def main():
    if len(sys.argv) < 2:
        print('Uso: python3 ml_full_item_data.py <ITEM_ID>')
        print('Ej: python3 ml_full_item_data.py MLA2567934822')
        sys.exit(1)

    item_id = sys.argv[1]
    print('Consultando: ' + item_id)

    try:
        app_id, client_secret = read_credentials()
        token = get_token(app_id, client_secret)
    except Exception as e:
        print('Error de autenticacion: ' + str(e))
        sys.exit(1)

    output = {'item_id': item_id}

    # 1. Description
    try:
        desc = api_get('https://api.mercadolibre.com/items/' + item_id + '/description', token)
        output['description'] = desc.get('plain_text', '')
    except Exception as e:
        output['description_error'] = str(e)

    # 2. Questions (last 5)
    try:
        qs = api_get('https://api.mercadolibre.com/questions/search?item=' + item_id + '&limit=5', token)
        output['questions_total'] = qs.get('total', 0)
        questions = []
        for q in qs.get('questions', []):
            qd = {
                'text': q.get('text', ''),
                'date': q.get('date_created', ''),
                'status': q.get('status', ''),
            }
            if q.get('answer'):
                qd['answer'] = {
                    'text': q['answer'].get('text', ''),
                    'date': q['answer'].get('date_created', ''),
                }
            questions.append(qd)
        output['questions'] = questions
    except Exception as e:
        output['questions_error'] = str(e)

    # 3. Seller info
    try:
        qs_resp = api_get('https://api.mercadolibre.com/questions/search?item=' + item_id + '&limit=1', token)
        first_qs = qs_resp.get('questions', [])
        if first_qs:
            sid = first_qs[0].get('seller_id')
            if sid:
                seller = api_get('https://api.mercadolibre.com/users/' + str(sid), token)
                output['seller'] = {
                    'id': sid,
                    'nickname': seller.get('nickname', ''),
                    'city': seller.get('address', {}).get('city', ''),
                    'state': seller.get('address', {}).get('state', ''),
                    'reputation_level': seller.get('seller_reputation', {}).get('level_id', ''),
                    'power_seller': seller.get('seller_reputation', {}).get('power_seller_status', ''),
                    'total_transactions': seller.get('seller_reputation', {}).get('transactions', {}).get('total', 0),
                }
    except Exception as e:
        output['seller_error'] = str(e)

    # Print as formatted JSON
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()