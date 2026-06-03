import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, '../docs/diagrams');
mkdirSync(OUT, { recursive: true });

const DIAGRAM = `graph TB
    subgraph Internet
        User([Workshop User])
        Admin([Platform Admin])
    end
    subgraph "Oracle Cloud Free Tier VM (4 OCPU, 24 GB RAM)"
        subgraph RP["Caddy Reverse Proxy"]
            CADDY[Caddy :80 / :443<br/>Auto Let's Encrypt TLS]
        end
        subgraph DC["Docker Compose Services"]
            FE[Frontend Next.js 16 :3000]
            API[Backend API FastAPI :8000]
            WK[Worker RQ Background Jobs]
            FC[FreeCAD Worker :8100 STEP/STL]
            PG[(PostgreSQL 16 :5432)]
            RD[(Redis 7 :6379)]
        end
        UV[Local Upload Storage /app/uploads/]
    end
    User -->|HTTPS :443| CADDY
    Admin -->|HTTPS :443| CADDY
    CADDY -->|/api/*| API
    CADDY -->|/*| FE
    API -->|read/write| PG
    API -->|enqueue / cache| RD
    API -->|STEP/STL export| FC
    WK -->|poll| RD
    WK -->|read/write| PG
    WK -->|read| UV
    WK -->|AI inference| AI[OpenCV / ONNX / CLIP in-worker]`;

const HTML = `<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <style>
    body { margin: 40px; background: white; display: flex; justify-content: center; }
    #diagram { max-width: 100%; }
  </style>
</head>
<body>
  <div class="mermaid">${DIAGRAM}</div>
  <script>mermaid.initialize({ startOnLoad: true, theme: 'default' });</script>
</body>
</html>`;

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });

  // Write HTML to temp file
  const tmpHtml = '/tmp/mermaid-deployment.html';
  writeFileSync(tmpHtml, HTML);

  await page.goto(`file://${tmpHtml}`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('.mermaid svg', { timeout: 15000 });
  await page.waitForTimeout(1000);

  // Find and screenshot the SVG
  const svg = await page.$('.mermaid');
  if (svg) {
    await svg.screenshot({ path: resolve(OUT, 'deployment-topology.png') });
    console.log('✓ deployment-topology.png');
  }

  await browser.close();
}

main().catch(console.error);
