# NestJS 12 Upgrade and Platform

Reference for moving from NestJS 11 to 12 and for the platform choices that changed in 12.x: ESM packages, CLI and tooling defaults, HTTP adapters, Standard Schema validation, configuration, built-in security helpers, Terminus, GraphQL packages and observability. Verified against the NestJS migration guide and documentation sources, and npm metadata for NestJS 12.3.2 (2026-10).

## 1. Upgrade procedure

1. Upgrade the CLI first, globally and locally, with TypeScript 6:

```bash
npm i -g @nestjs/cli@latest @nestjs/schematics@latest
npm i -D @nestjs/cli@latest @nestjs/schematics@latest typescript@^6
```

2. If npm reports a peer conflict, an older `ts-jest` or `typescript-eslint` in the lockfile usually does not accept TypeScript 6: run `npm update ts-jest typescript-eslint`, then repeat.
3. Run `nest upgrade --dry-run` to see the report, then `nest upgrade`. It moves every recognized `@nestjs/*` package to its v12-compatible major together, bumps TypeScript to 6, applies mechanical changes (`nest-cli.json` webpack options, GraphQL `playground` and subscription transport options, the NATS package swap, `@nestjs/config` validation options) and prints notes on behavioral changes it cannot migrate.
4. All Nest packages must move to the same major at once.
5. Run the test suite and read section 3 below for behavior changes.

Node.js requirements:

| Activity | Minimum Node.js |
|---|---|
| Running a Nest 12 application | 20.19+, or 22.12+ on the 22.x line (21.x unsupported) |
| `nest new`, `nest generate`, `nest upgrade` (`@nestjs/schematics`) | 22.22.3+, 24.15+ or 26+ |

`@nestjs/core` declares `node >= 20`, but the packages are ESM-only and CommonJS apps load them through `require(esm)`, unflagged from Node 20.19 and 22.12. AWS Lambda disables `require(esm)` by default on its Node 20, 22 and 24 runtimes; set `NODE_OPTIONS=--experimental-require-module` (appended to existing options) to run a CommonJS Nest 12 app there.

## 2. ESM and CommonJS

- All core Nest packages ship as ESM. A CommonJS application can upgrade and stay CommonJS; `nest upgrade` does not change the module format.
- `nest new` asks for a CommonJS or ESM layout. ESM projects use Vitest; CommonJS projects use Jest. All generated projects use oxlint.
- Switching your own code to ESM is optional. Steps: add `"type": "module"` to `package.json`; for projects older than schematics 11.0.6 set `"module": "nodenext"`, `"moduleResolution": "nodenext"`, `"resolvePackageJsonExports": true`, `"target": "ES2023"` first.
- In ESM source: relative imports carry the `.js` extension (`import { AppModule } from './app.module.js'`), `__dirname` becomes `import.meta.dirname`, `require` becomes `createRequire(import.meta.url)`, and `bootstrap()` can be awaited at top level.
- Generated ESM `compilerOptions` include `emitDecoratorMetadata`, `experimentalDecorators`, `isolatedModules`, `strict` with `strictPropertyInitialization: false`, and `types` for Vitest and Node.
- `nest-cli.json` and `tsconfig.build.json` are identical for both variants.
- OpenTelemetry in a CommonJS app that depends on ESM-only Nest packages: instrumentations that patch `require()` do not patch packages imported by ESM dependencies (for example Express imported by `@nestjs/platform-express`). The OpenTelemetry JS ESM document describes the loader hook that fixes this.

## 3. Behavior changes to review

- **Lifecycle hook ordering**: hooks (`onModuleInit`, `onApplicationBootstrap`, shutdown hooks) are called by component hierarchy level, which can reorder hooks between dependent providers.
- **`@Optional()` inheritance**: a subclass that declares its own constructor no longer inherits the parent constructor's optional markers; Nest throws `UnknownDependenciesException` where v11 injected `undefined`. Redeclare `@Optional()` in the subclass. From 12.1 a subclass without its own constructor keeps the parent's markers.
- **Terminus**: the legacy `HealthIndicator` base class and `HealthCheckError` were removed. Custom indicators inject `HealthIndicatorService`, call `check(key)` and return `indicator.up()`/`indicator.down(details)`, or use `.attempt(fn).withTimeout(ms)`. The `timeout` option of built-in indicators is deprecated in favor of `.withTimeout()`.
- **GraphQL**: GraphiQL is the default IDE (`graphiql: { ... }` options object); `subscriptions-transport-ws` support is removed, use `graphql-ws` (`subscriptions: { 'graphql-ws': true }`).
- **NATS v3**: replace `nats` with `@nats-io/transport-node` (and `@nats-io/nats-core` for helpers such as `headers()`); packets are serialized as JSON strings and custom deserializers get the full message (`msg.json()`).
- **Logger**: `ConsoleLogger` treats plain objects after the message as structured params (nested under `params` in JSON mode, or spread with `flattenParams`); set `structuredParams: false` to restore the old output.
- **Pipes**: `PipeTransform` signatures are stricter and `ArgumentMetadata` is generic; custom pipes with hand-written signatures may need type updates.
- **Config**: `validationSchema` is no longer Joi-specific; Joi must be v18 or later; library-specific options move under `validationOptions.libraryOptions`. Joi keeps its defaults `allowUnknown: true` and `abortEarly: false`.
- **HTTP adapter error mapping** was reworked for core, Express and Fastify; the Express adapter drains in-flight requests on shutdown.
- **Jest** can load the ESM-only packages only on Node 24.9+; `nest upgrade` bumps Jest to 30.

## 4. New capabilities

- **Standard Schema validation**: `schema` option on `@Body()`, `@Query()`, `@Param()`, `@RawBody()`, `@MessageBody()` and `@Payload()`, validated by `StandardSchemaValidationPipe` (from `@nestjs/common`). Works with Zod, Valibot and ArkType. `z.object()` strips unknown keys; `z.strictObject()` rejects them. `StandardSchemaSerializerInterceptor` with `@SerializeOptions({ schema })` shapes responses. `ValidationPipe` plus class-validator remains fully supported.
- **`ValidationPipe` `errorFormat`**: `'list'` (default) returns an array of message strings; `'grouped'` returns an object keyed by property path.
- **Machine-readable errors**: `throw new BadRequestException('Password is too weak', { errorCode: 'WEAK_PASSWORD' })` serializes `errorCode` in the response body.
- **Route conflict diagnostics**: `NestFactory.create(AppModule, { routeConflictPolicy: { duplicate: 'error', shadow: 'warn' }, routeResolutionStrategy: 'specificity' })`; both are opt-in.
- **Security helpers (12.1+)**: `app.useSecurityHeaders()` sets Helmet-8-equivalent headers on Express and Fastify without an extra package; `app.enableCsrfProtection()` rejects cross-origin state-changing requests using `Sec-Fetch-Site` and `Origin`, with `trustedOrigins` and `exclude` options; browsers send these headers, and requests without them (non-browser clients) are allowed, so it targets cookie-authenticated browser use. Call both right after `NestFactory.create()` and before `listen()`.
- **Authentication and authorization packages**: `@nestjs/authentication` (sessions, password hashing, email verification, TOTP, magic links, OIDC, tokens, API keys) and `@nestjs/authorization` (policy classes) exist as 0.x releases in this period. Check their current version, stability and documentation before adopting; `@nestjs/jwt` and `@nestjs/passport` remain available for token verification.
- **Observability**: `@nestjs/observe` (`createObserveModule()`, `instrument` option on `NestFactory.create`) reports requests, jobs and errors in terms of controllers, providers and queue consumers.
- **Other**: `Reflector.createDecorator()` form for the `decorator` schematic, request-scoped WebSocket gateways, `handleDisconnect` with a reason, a microservices pre-request hook, `GrpcExceptionFilter`, regex patterns for Kafka handlers.

## 5. CLI and build

- Rspack is the default bundler for monorepos; `--webpack`/`--webpackPath` and the `nest-cli.json` `webpack`/`webpackConfigPath` options are deprecated in favor of `--builder rspack` and `--rspackPath`.
- `bun` is a supported package manager; the `angular` schematic was removed.
- New flags: `--emit-declarations` (SWC builder), `--no-type-check`, `--silent`, `nest build --all --parallel [n]` for monorepos, `includeLibraryAssets` in `nest-cli.json`.
- `nest start --env-file .env` passes the file to Node's `--env-file`, so variables exist before `ConfigModule` loads; `ConfigModule` treats them as predefined and validates them only while `validatePredefined` stays `true`.
- `nest deploy` forwards to Mau (`@nestjs/mau`).

## 6. HTTP adapters

| Adapter | Package | Notes |
|---|---|---|
| `ExpressAdapter` (default) | `@nestjs/platform-express` | Express 5; widest middleware compatibility |
| `FastifyAdapter` | `@nestjs/platform-fastify` | Fastify 5; plugins, `@RouteConfig()`, `@RouteConstraints()`; listen on `'0.0.0.0'` to accept non-local connections; use `@fastify/helmet` or `useSecurityHeaders()`; use Fastify-compatible middleware that receives raw `req` and `res` |
| `NodeAdapter` | `@nestjs/platform-node` | Runs on `node:http` with Express-style helpers; recommended by the docs since 12.3 |

`NodeAdapter` differences from Express: routes match by specificity, paths are case-sensitive, route parameters are capped at 100 characters (`maxParamLength`), returned strings are sent as `text/plain`, JSON bodies with `__proto__` or `constructor.prototype` keys are rejected (`onProtoPoisoning`), `trustProxy` takes a trust specification (not a hop count) and should list only known proxies, and `res.render()`, `res.download()`, `res.format()`, `req.accepts()` and mounting an Express app are unavailable. The `@nestjs/apollo` driver works with it (14.1.1+); `@nestjs/mercurius` requires Fastify.

```ts
import { NestFactory } from '@nestjs/core';
import { type NestNodeApplication, NodeAdapter } from '@nestjs/platform-node';
import { AppModule } from './app.module.js';

const app = await NestFactory.create<NestNodeApplication>(AppModule, new NodeAdapter({ trustProxy: 'loopback' }));
await app.listen(process.env.PORT ?? 3000);
```

```ts
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';

const app = await NestFactory.create<NestFastifyApplication>(AppModule, new FastifyAdapter());
await app.listen(process.env.PORT ?? 3000, '0.0.0.0');
```

## 7. Configuration with a schema

```ts
import { ConfigModule } from '@nestjs/config';
import { z } from 'zod';

ConfigModule.forRoot({
  isGlobal: true,
  cache: true,
  validationSchema: z.object({
    NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
    PORT: z.coerce.number().default(3000),
    DATABASE_URL: z.url(),
    JWT_SECRET: z.string().min(32),
  }),
});
```

- Validation covers environment variables only; values returned from `registerAs()` factories or config files are not validated automatically.
- Prefer `ConfigService.getOrThrow()` for required values.
- Variables already in the real environment win over `.env` file values.
- Load order matters in tests: `forRoot()` runs when the module file is imported.

## 8. GraphQL package compatibility

`@nestjs/graphql` 14.1 accepts `graphql` 16.11+ or 17 and TypeScript 5.5+ or 6. `@nestjs/apollo` 14.1 requires `@apollo/server` 5, and `@apollo/server` 5.5 declares `graphql` 16.11+ as its peer dependency, so an Apollo-driver application stays on `graphql` 16 until Apollo Server publishes support for 17. `@nestjs/mercurius` declares `graphql` 16 as well. Check the peer ranges of the driver you use before upgrading `graphql`. Schema design guidance lives in graphql-expert.
