import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
function walk(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(p,e.name)):[path.join(p,e.name)]);}
const files=['server.mjs',...walk('public').filter(f=>f.endsWith('.js'))];
for(const file of files){const r=spawnSync(process.execPath,['--check',file],{stdio:'inherit'});if(r.status)process.exit(r.status);}
console.log(`${files.length} JavaScript modules checked`);
