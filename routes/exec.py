from pyrevit import script, revit, DB
from pyrevit.routes import route

@route('/revit/exec', methods=['POST'])
def exec_script(request):
    data = request.json
    code = data.get('code', '')
    
    if not code:
        return {'status': 'error', 'message': 'No code provided'}
    
    output = []
    def log(msg):
        output.append(str(msg))
        
    local_scope = {
        'doc': revit.doc,
        'uidoc': revit.uidoc,
        'DB': DB,
        'print': log
    }
    
    try:
        with revit.Transaction('AI Script Execution'):
            exec(code, local_scope)
        return {'status': 'success', 'output': '\n'.join(output)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
