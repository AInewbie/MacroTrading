import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const publicRoot = fileURLToPath(new URL('./public/', import.meta.url));
const sourceRoot = fileURLToPath(new URL('./src/', import.meta.url));
const portArg = process.argv.find((value) => value.startsWith('--port='));
const requestedPort = Number(portArg?.split('=')[1] || process.env.PORT || 4173);
const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json',
};

const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const sourceRequest = pathname.startsWith('/src/');
    const root = sourceRequest ? sourceRoot : publicRoot;
    const relative = pathname === '/' ? 'index.html' : pathname.replace(sourceRequest ? /^\/src\// : /^\//, '');
    const candidate = normalize(join(root, relative));
    if (!candidate.startsWith(root)) throw new Error('Invalid path');
    let file = candidate;
    if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    response.writeHead(200, {
      'content-type': types[extname(file)] || 'application/octet-stream',
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    });
    response.end(await readFile(file));
  } catch (error) {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Not found');
  }
});

server.listen(requestedPort, '127.0.0.1', () => {
  const address = server.address();
  console.log(`MacroTrading is ready at http://127.0.0.1:${address.port}`);
  console.log('Paper execution only. Live brokerage routes are disabled.');
});
