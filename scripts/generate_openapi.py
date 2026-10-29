"""Generate a portable OpenAPI description matching the Flask route table."""
import json
import re
from brainage import ROOT, create_app

def shape(value):
    """Conservative schema from a redacted example; optional and nullable fields may vary."""
    if isinstance(value, dict):
        return {'type': 'object', 'properties': {k: shape(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {'type': 'array', 'items': shape(value[0]) if value else {}}
    if value is None:
        return {'description': 'Observed null; see API.md for allowed values.'}
    kind = 'boolean' if isinstance(value, bool) else 'number' if isinstance(value, (int, float)) else 'string'
    return {'type': kind, 'nullable': True}

def response_examples():
    collection = json.loads((ROOT / 'postman/BrainAgeConnect.postman_collection.json').read_text(encoding='utf-8'))
    result = {}
    for item in collection['item']:
        for example in item.get('response', []):
            if example['code'] not in (200, 201) or 'application/json' not in str(example.get('header', [])):
                continue
            url = item['request']['url'].split('?', 1)[0].replace('{{base_url}}', '/api/v1')
            url = re.sub(r'\{\{[^}]+\}\}', '{}', url)
            try:
                body = json.loads(example['body'])
            except (ValueError, KeyError):
                continue
            result.setdefault((item['request']['method'], url, str(example['code'])), body)
    return result

def main():
    app = create_app()
    string = {'type': 'string'}
    age = {'type': 'number', 'minimum': 20, 'maximum': 80, 'nullable': True}
    sample = {'type': 'object', 'additionalProperties': False, 'properties': {
        'sample_code': {'type': 'string', 'pattern': '^[A-Za-z0-9_.-]+$', 'maxLength': 120},
        'age_at_scan_weeks': age, 'birth_age_weeks': {'type': 'number', 'minimum': 20, 'maximum': 45, 'nullable': True},
        'sex': {'type': 'string', 'enum': ['Female', 'Male', 'Unknown']},
        'has_dmri': {'type': 'boolean'}, 'has_fmri': {'type': 'boolean'},
        'status': {'type': 'string', 'enum': ['registered', 'ready', 'processing', 'completed', 'failed']},
        'visibility': {'type': 'string', 'enum': ['private', 'shared']}, 'description': {'type': 'string', 'maxLength': 2000}}}
    note = {'type': 'object', 'additionalProperties': False, 'properties': {
        'text': {'type': 'string', 'minLength': 1, 'maxLength': 4000},
        'category': {'type': 'string', 'enum': ['research', 'quality', 'review']}}}
    analysis = {'type': 'object', 'additionalProperties': False, 'properties': {
        'modality': {'type': 'string', 'enum': ['dmri', 'fmri', 'combined']},
        'estimated_age_weeks': {'type': 'number', 'minimum': 20, 'maximum': 80},
        'method': {'type': 'string', 'minLength': 1, 'maxLength': 120},
        'model_version': {'type': 'string', 'minLength': 1, 'maxLength': 120},
        'provenance': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
        'quality_score': {'type': 'number', 'minimum': 0, 'maximum': 1, 'nullable': True}}}
    schemas = {'SampleInput': sample, 'NoteInput': note, 'AnalysisInput': analysis,
        'Login': {'type': 'object', 'additionalProperties': False, 'required': ['username', 'password'],
            'properties': {'username': string, 'password': {'type': 'string', 'format': 'password'}}},
        'Register': {'type': 'object', 'additionalProperties': False, 'required': ['username', 'password', 'display_name'],
            'properties': {'username': string, 'password': {'type': 'string', 'format': 'password'}, 'display_name': string}},
        'PasswordChange': {'type': 'object', 'additionalProperties': False, 'required': ['current_password', 'new_password'],
            'properties': {'current_password': {'type': 'string', 'format': 'password'}, 'new_password': {'type': 'string', 'format': 'password'}}},
        'UserUpdate': {'type': 'object', 'additionalProperties': False, 'minProperties': 1,
            'properties': {'active': {'type': 'boolean'}, 'role': {'type': 'string', 'enum': ['admin', 'researcher']}}},
        'Error': {'type': 'object', 'properties': {'error': {'type': 'object', 'properties': {
            'status': {'type': 'integer'}, 'message': string}}}}}
    document = {'openapi': '3.0.3', 'info': {'title': 'BrainAge Connect', 'version': '1.0.0',
        'description': 'Research metadata and precomputed-result management. No MRI-to-brain-age inference. All ages are postmenstrual weeks. See API.md for permissions and examples.'},
        'servers': [{'url': 'http://127.0.0.1:5000'}, {'url': 'http://127.0.0.1:5001'}],
        'security': [{'BearerAuth': []}], 'paths': {}, 'components': {
            'securitySchemes': {'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}}, 'schemas': schemas}}
    filters = {'q': string, 'age_min': {'type':'number','minimum':20,'maximum':80}, 'age_max': {'type':'number','minimum':20,'maximum':80},
        'modality': {'type':'string','enum':['dmri','fmri','both','neither']},
        'source': {'type':'string','enum':['dhcp_local','manual','synthetic']},
        'status': sample['properties']['status'], 'sex': sample['properties']['sex']}
    examples = response_examples()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith('/api/v1/'):
            continue
        path = re.sub(r'<([^>]+)>', r'{\1}', rule.rule)
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            status = '204' if method == 'DELETE' or path.endswith('/logout') else '201' if method == 'POST' and not path.endswith('/login') else '200'
            operation = {'operationId': rule.endpoint.replace('.', '_') + '_' + method.lower(),
                'summary': rule.endpoint.split('.')[-1].replace('_', ' ').capitalize(),
                'description': 'Authenticated resource. PUT and PATCH update only supplied editable fields; omitted fields remain unchanged.' if method in ('PUT','PATCH') else 'See docs/API.md for data semantics and authorization.',
                'responses': {status: {'description': 'Success'}, **{str(code): {'description': text,
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}
                    for code,text in [(400,'Invalid input'),(401,'Missing/expired/revoked session'),(403,'Insufficient permission'),(404,'Not found or not visible'),(409,'Duplicate/concurrent conflict'),(415,'JSON content type required'),(503,'Database unavailable')]}}}
            if status != '204':
                example_key = (method, re.sub(r'\{[^}]+\}', '{}', path), status)
                example = examples.get(example_key)
                if example is None and method == 'PATCH':
                    example = examples.get(('PUT', example_key[1], status))
                schema = shape(example) if example is not None else {'type': 'object', 'description': 'JSON response; see API.md for fields.'}
                operation['responses'][status]['content'] = {'application/json': {'schema': schema}}
                if example is not None:
                    operation['responses'][status]['content']['application/json']['example'] = example
                    operation['responses'][status]['description'] += '; schema describes fields observed in a redacted synthetic example and is not exhaustive.'
            if path.endswith(('/login','/register','/health','/openapi.json')):
                operation['security'] = []
            parameters = [{'name': name, 'in':'path','required':True,'schema':{'type':'string','pattern':'^[a-fA-F0-9]{24}$'}} for name in rule.arguments]
            query = {}
            if method == 'GET':
                if path.endswith('/samples') or '/statistics/' in path or '/exports/' in path:
                    query.update(filters)
                if path.endswith(('/samples','/notes','/analyses','/users','/audit-logs')):
                    query.update(page={'type':'integer','minimum':1,'maximum':1000000,'default':1}, page_size={'type':'integer','minimum':1,'maximum':100,'default':20})
                if path.endswith('/samples'):
                    query['sort']={'type':'string','enum':['sample_code','age_at_scan_weeks','created_at','updated_at'],'default':'sample_code'}
                elif path.endswith(('/notes','/analyses')):
                    query['sort']={'type':'string','enum':['created_at','updated_at'],'default':'created_at'}
                if 'sort' in query:
                    query['order']={'type':'string','enum':['asc','desc'],'default':'asc'}
                if path.endswith('/statistics/maturity'):
                    query.update(method={'type':'string','maxLength':120}, model_version={'type':'string','maxLength':120}, group_by={'type':'string','enum':['overall','age_group'],'default':'overall'})
                if path.endswith('/statistics/comparison'):
                    query.update({name: {'type':'string','maxLength':120} for name in ('dmri_method','dmri_model_version','fmri_method','fmri_model_version')})
                if '/exports/' in path:
                    query['format']={'type':'string','enum':['json','csv'],'default':'json'}
                    operation['responses']['200']['content']={'application/json':{'schema':{'type':'object'}},'text/csv':{'schema':{'type':'string'}}}
            parameters.extend({'name':k,'in':'query','schema':v} for k,v in query.items())
            if parameters:
                operation['parameters']=parameters
            schema_name = None
            required=[]
            if method in ('POST','PUT','PATCH'):
                if '/notes' in path:
                    schema_name='NoteInput'; required=['text']
                elif '/analyses' in path:
                    schema_name='AnalysisInput'; required=['modality','estimated_age_weeks','method','model_version','provenance']
                elif '/samples' in path:
                    schema_name='SampleInput'; required=['sample_code','age_at_scan_weeks']
                elif path.endswith('/register'): schema_name='Register'
                elif path.endswith('/login'): schema_name='Login'
                elif path.endswith('/password'): schema_name='PasswordChange'
                elif '/users/' in path: schema_name='UserUpdate'
            if schema_name:
                schema={'allOf':[{'$ref':'#/components/schemas/'+schema_name}]}
                if method == 'POST' and required: schema['allOf'].append({'required':required})
                if method in ('PUT','PATCH'): schema['allOf'].append({'minProperties':1})
                operation['requestBody']={'required':True,'content':{'application/json':{'schema':schema}}}
            document['paths'].setdefault(path,{})[method.lower()]=operation
    (ROOT/'docs/openapi.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    print('OpenAPI operations:',sum(len(p) for p in document['paths'].values()))

if __name__ == '__main__':
    main()
