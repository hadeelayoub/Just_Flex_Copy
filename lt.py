import json
from watson_developer_cloud import LanguageTranslatorV2
import sys

language_translator = LanguageTranslatorV2(
    username='0da2e597-d264-4acd-8639-2428373ebfdc',
    password='4WgFNFxexx8o')

language_translator.get_models()
language_translator.get_model('en-es-conversational')

sys.stdout.write(json.dumps(language_translator.translate('Hello, world!', source='en', target='es'), indent=2,
                 ensure_ascii=False))
sys.stdout.write('\n')