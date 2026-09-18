"""Single-user local HTTP application. No external bind or live execution routes."""
from __future__ import annotations
import argparse
import json
import mimetypes
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote
from .service import Service
from .storage import Conflict
from .validation import canonical
from .ingestion import parse_market_csv

class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,service):
        self.service=service;self.csrf=secrets.token_urlsafe(32);super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    server_version='MacroTrading/0.5'
    def log_message(self,fmt,*args):pass
    def host_valid(self):
        port=self.server.server_address[1]
        return self.headers.get('Host') in (f'127.0.0.1:{port}',f'localhost:{port}')
    def send(self,value,status=200,kind='application/json; charset=utf-8',filename=None,report=False):
        data=canonical(value).encode() if kind.startswith('application/json') else value.encode() if isinstance(value,str) else value
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        style="'unsafe-inline'" if report else "'self'"
        script = "'none'" if report else "'self'"
        self.send_header('Content-Security-Policy',f"default-src 'self'; script-src {script}; style-src {style}; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if not self.host_valid():return self.send({'error':'Host rejected'},403)
        path=unquote(urlsplit(self.path).path);service=self.server.service
        try:
            if path=='/api/state':return self.send({**service.snapshot(),'csrf_token':self.server.csrf})
            if path=='/api/health':return self.send({'status':'ok','version':'0.5.0'})
            if path=='/api/export':return self.send(service.export(),filename='macrotrading-workspace.json')
            if path=='/api/backup':return self.send(service.backup(),filename='macrotrading-state-backup.json')
            if path.startswith('/api/runs/'):
                parts=path.split('/');run=service.store.run(parts[3])
                if len(parts)==5 and parts[4]=='html':return self.send(run['html'],kind='text/html; charset=utf-8',report=True)
                return self.send({k:v for k,v in run.items() if k!='html'},filename='macrotrading-run-'+parts[3]+'.json')
            if path=='/api/example':return self.send(json.loads((service.root/'examples/integrated_research_run.json').read_text()))
            if path=='/guide':
                return self.send((service.root/'docs/user-guide.html').read_text(),kind='text/html; charset=utf-8',report=True)
            if path.startswith('/examples/'):
                target=(service.root/path.lstrip('/')).resolve();root=(service.root/'examples').resolve()
            else:
                root=(service.root/'public').resolve();target=(root/('index.html' if path=='/' else path.lstrip('/'))).resolve()
            if not target.is_relative_to(root) or not target.is_file() or target.suffix not in ('.html','.js','.css','.json','.csv','.svg'):return self.send({'error':'Not found'},404)
            kind=mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            return self.send(target.read_bytes(),kind=kind)
        except (ValueError,KeyError,FileNotFoundError) as exc:return self.send({'error':str(exc)},404)
        except Exception:return self.send({'error':'Read failed. Your stored data has not been reset.'},500)
    def do_POST(self):
        if not self.host_valid():return self.send({'error':'Host rejected'},403)
        origin=self.headers.get('Origin');host=self.headers.get('Host')
        if origin and origin not in (f'http://{host}',f'https://{host}'):return self.send({'error':'Cross-origin request rejected'},403)
        if self.headers.get('X-MacroTrading-Token')!=self.server.csrf:return self.send({'error':'Reload the application to obtain a valid request token'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8_000_000:return self.send({'error':'Request must contain 1 byte to 8 MB of JSON'},413)
            if not self.headers.get('Content-Type','').startswith('application/json'):return self.send({'error':'JSON required'},415)
            body=json.loads(self.rfile.read(size),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('non-finite JSON number')))
            if not isinstance(body,dict):raise ValueError('request body must be an object')
            path=urlsplit(self.path).path;s=self.server.service
            routes={'/api/run':s.run,'/api/workspace/save':s.save_workspace,'/api/workspace/import':s.import_workspace,'/api/config/save':s.save_config,'/api/decision':s.decision,'/api/orders/stage':s.stage,'/api/orders/execute':s.execute,'/api/orders/cancel':s.cancel_order,'/api/proposal':s.propose,'/api/sources/save':s.save_sources,'/api/inbox/accept':s.accept_candidate,'/api/inbox/reject':s.reject_candidate,'/api/fx/apply':s.apply_fx,'/api/ai/extract':s.extract,'/api/evaluate':s.evaluate,'/api/reconcile':s.reconcile,'/api/restore':s.restore}
            if path in routes:result=routes[path](body)
            elif path=='/api/sources/refresh':result=s.refresh_sources()
            elif path=='/api/rebalance':result=s.rebalance()
            elif path=='/api/market/csv':result=parse_market_csv(body['csv'])
            elif path=='/api/run/example':result=s.run(json.loads((s.root/'examples/integrated_research_run.json').read_text()))
            else:return self.send({'error':'Unknown action'},404)
            self.send(result)
        except Conflict as exc:self.send({'error':str(exc)},409)
        except (ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)},400)
        except sqlite3.Error:self.send({'error':'Database operation failed; the transaction was rolled back.'},500)
        except Exception:self.send({'error':'Operation failed; no partial database transaction was committed.'},500)

def main():
    p=argparse.ArgumentParser(description='MacroTrading local research and paper portfolio server');p.add_argument('--port',type=int,default=4173);p.add_argument('--data-dir',default=None)
    args=p.parse_args();root=Path(__file__).resolve().parents[2];data=Path(args.data_dir).expanduser() if args.data_dir else root/'var'
    service=Service(root,data);server=AppServer(('127.0.0.1',args.port),service)
    print(f'MacroTrading v0.5: http://127.0.0.1:{server.server_address[1]}',flush=True);print(f'Data: {service.store.path} | Paper only',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
