"""A timed-out circuit must leave evidence and allow the next one to execute."""
import json
import pathlib
import runpy
import subprocess
from unittest.mock import patch

api = runpy.run_path(str(pathlib.Path(__file__).with_name('blind-campaign.py')))
request = b'{"n":50}'
digest = api['sha'](request)
completed = {'inputSHA256': digest, 'status': 'COMPLETED'}
responses = [
    subprocess.TimeoutExpired('audit', 21),
    subprocess.CompletedProcess([], 0, b'null', b''),
    subprocess.CompletedProcess([], 0, json.dumps(completed).encode(), b''),
]
with patch('subprocess.run', side_effect=responses):
    timeout, malformed, success = [api['audited_case'](request, 1, 2048) for _ in responses]
assert timeout['status'] == malformed['status'] == 'FAILED'
assert timeout['inputSHA256'] == malformed['inputSHA256'] == digest
assert timeout['timeoutSeconds'] == 21
assert success == completed
print('PASS: timeout, malformed report, and next completed circuit')

# Score through the public protocol with genuine commitments and a synthetic
# worker report. A real-only amplitude payload must remain incomplete.
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    root = pathlib.Path(tmp)
    challenge, reference, commitment, reveal = [root / name for name in
        ('challenge.json', 'reference.json', 'commitment.json', 'reveal.json')]
    request = {'n': 1, 'gates': [{'name':'x','q':0,'controls':[]}],
               'queries': [{'id':'a','kind':'amplitude','prefix':1,'bits':'1'}]}
    suite = {'schema':'DSIQ-blind-challenge-v1','suiteId':'smoke',
             'circuits':[{'id':'one','family':'RCS','request':request}]}
    api['write'](challenge, suite)
    api['write'](reference, {'schema':'DSIQ-blind-reference-v1','suiteId':'smoke',
        'referenceMethod':'Pauli X applied to zero','circuits':{'one':{'a':{
        'real':1,'imag':0,'absoluteTolerance':1e-13,'relativeTolerance':1e-9}}}})
    api['commit'](challenge, reference, commitment, reveal, False)
    source = api['freeze']()['sourceSHA256']
    digest = api['sha'](api['encode'](request))
    for label, value, expected in [('complete', {'real':1,'imag':0}, True),
                                   ('missing-imaginary', {'real':1}, False)]:
        out = root / label
        worker = {'status':'COMPLETED','inputSHA256':digest,'outputs':[
            {'id':'a','kind':'amplitude','prefix':1,'value':value}]}
        audit = {'status':'COMPLETED','workerExitCode':0,
                 'inputSHA256':digest,'workerReport':worker}
        with patch.dict(api['execute'].__globals__, {'audited_case':lambda *_: audit}):
            run = api['execute'](challenge, commitment, out, source, 1, 2048)
        score = api['score'](challenge, commitment, reveal, out, run['outputManifestSHA256'])
        assert score['numericalPass'] is expected
        assert score['test100Certified'] is False
print('PASS: complete complex amplitude accepted, missing imaginary component rejected')
