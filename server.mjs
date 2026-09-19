// Compatibility launcher. The Python service is the single application backend.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const python=process.env.MACROTRADING_PYTHON||(process.platform==='win32'?'python':'python3');
const child=spawn(python,[fileURLToPath(new URL('./run.py',import.meta.url)),...process.argv.slice(2)],{stdio:'inherit'});
child.on('error',()=>{console.error('Python 3.11+ is required. Run python3 run.py directly.');process.exitCode=1;});
child.on('exit',code=>process.exitCode=code??1);
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
