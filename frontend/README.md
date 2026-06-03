<<<<<<< HEAD
<<<<<<< HEAD
# RetroMind AI — Frontend

Next.js 16 frontend for the RetroMind AI EV retrofit assessment platform.

## Stack

- Next.js 16 (App Router, standalone output)
- Tailwind CSS 4
- TypeScript
- Three.js / React Three Fiber (digital twin visualization)

## Development

```bash
npm install
npm run dev
```

Frontend runs at http://localhost:3000. API expects `NEXT_PUBLIC_API_URL` environment variable (defaults to `http://localhost:8000/api/v1`).

## Build

```bash
npm run build
```

Produces standalone output in `.next/` (config: `output: "standalone"` in `next.config.ts`).

## Deployment

Containerized via Dockerfile (multi-stage: builder → runner). Deployed behind Caddy reverse proxy on OCI.
=======
=======
>>>>>>> origin/main
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
