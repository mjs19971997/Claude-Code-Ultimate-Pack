# Express 4 to 5 Migration

This file lists the breaking changes that affect application code when moving from Express 4 to Express 5 (current 5.3.0, Node.js 18 or later). Each behavior below was checked against express 5.3.0 and path-to-regexp v8; check the official migration guide (expressjs.com, `/en/guide/migrating-5.html`) for anything not listed here.

## 1. Order of work

1. Upgrade on a branch: `npm install express@5` and the matching `@types/express@5`. Raise the Node.js engine to a supported LTS (22, 24 or 26; Express 5 itself needs 18 or later).
2. Run the official codemod recipe: `npx codemod @expressjs/v5-migration-recipe`. It rewrites `res.redirect('back')`, `req.param()`, singular `req.acceptsCharset`-style methods, argument order of `res.send/json/redirect`, `res.sendfile`, `app.del`, `express.static` dotfile options and `express.static.mime`. Review the diff; it does not convert route strings.
3. Convert route path strings by hand (section 2).
4. Fix the request-object differences (section 3) and removed APIs (section 4).
5. Upgrade middleware that depends on Express internals (session stores, body-parser plugins, old `express-async-errors`); remove `express-async-errors`, which is no longer needed.
6. Run the test suite with the app started under `NODE_ENV=production` as well; path errors throw when the route is registered, so they appear at startup.

## 2. Route path syntax (path-to-regexp v8)

Invalid patterns throw at registration (for example `Missing parameter name at index 2: /*`).

| Express 4 | Express 5 | Note |
|---|---|---|
| `'/*'` | `'/*splat'` | `req.params.splat` is an array of segments |
| `'/files/*'` | `'/files/*splat'` | does not match `/files` itself |
| `'*'` (match everything, root included) | `'/{*splat}'` | braces make the wildcard optional |
| `'/:id?'` | `'/{:id}'` or `'/items{/:id}'` | `?` is no longer valid |
| `'/ab?cd'` | `'/a{b}cd'` | optional pieces use braces |
| `'/(.*)'` | `'/*splat'` | inline regex groups are gone |
| `'/:id(\\d+)'` | validate `id` in the handler or with `router.param` | regex in params removed |
| `'/(a\|b)'` | register two routes, or an array of paths | |

Reserved characters `()[]?+!` must be escaped with a backslash to match literally. A wildcard name (`splat` here) is arbitrary but must exist.

```typescript
app.get('/files/*splat', (req, res) => {
  const parts = req.params.splat as string[];   // ['a', 'b', 'c'] for /files/a/b/c
  // never join `parts` into a filesystem path without resolving and checking it against a base directory
});
app.get('/items{/:id}', (req, res) => { res.json({ id: req.params.id ?? null }); });
```

`req.params` values for unmatched optional parameters are absent (`undefined`), not empty strings.

## 3. Request and response behavior changes

- **Rejected promises**: an `async` handler or middleware that throws or rejects calls `next(err)`. Code that wrapped handlers for this can drop the wrapper; do not call `next(err)` and also rethrow.
- **`req.query`** is a getter; `req.query = {...}` throws (`Cannot set property query ... which has only a getter`). Middleware that sanitized `req.query` in place must write the cleaned copy somewhere else (`res.locals`, or a typed property on the request).
- **`query parser` default is `"simple"`**: `?a[b]=1&c=1&c=2` gives `{ 'a[b]': '1', c: ['1', '2'] }`, not nested objects. Set `app.set('query parser', 'extended')` only if clients depend on nested keys, and cap the depth and array length through schema validation.
- **`req.body` is `undefined`** when no body parser matched (Express 4 gave `{}`). `const { a } = req.body` throws on a request without a parser. Parse with a schema that rejects `undefined`.
- **`express.urlencoded()`** defaults to `extended: false` (the `querystring` parser).
- **`res.status(code)`** accepts only integers 100 to 999; `res.status('200')` throws.
- **`res.redirect('back')`** and `res.location('back')` are no longer special; they redirect to the relative URL `back`. Redirect to an explicit internal path. If the Referer is used, treat it as untrusted input and check that it is a same-origin path.
- **Removed signatures**: `res.redirect(url, status)` throws (use `res.redirect(status, url)`); `res.json(obj, status)` no longer sets the status (use `res.status(status).json(obj)`); `res.send(404)` sends the text `404` with status 200 (use `res.sendStatus(404)` or `res.status(404).send(...)`).
- **`req.host`** now includes the port when present; `req.hostname` stays without it.

## 4. Removed or renamed APIs

- `app.del()` removed: use `app.delete()`.
- `req.param(name)` removed: read `req.params`, `req.body` or `req.query` explicitly (which also removes the ambiguity about which source won).
- `res.sendfile()` removed: use `res.sendFile()` (needs an absolute path or a `root` option).
- `req.acceptsCharset`, `req.acceptsEncoding`, `req.acceptsLanguage` are now plural: `acceptsCharsets`, `acceptsEncodings`, `acceptsLanguages`.
- `express.static.mime` removed: use the `mime-types` package.
- Body parsing: `express.json`, `express.urlencoded`, `express.raw` and `express.text` are backed by body-parser 2.x.

## 5. Verification checklist

- [ ] App starts: no `Missing parameter name` or `Unexpected ?` errors from route strings.
- [ ] No code assigns to `req.query`.
- [ ] Every handler that reads `req.body` is behind a parser and handles `undefined`.
- [ ] No `res.redirect('back')`; redirect targets are validated.
- [ ] Error middleware still has four parameters and now also catches async rejections.
- [ ] Third-party middleware versions support Express 5 (check each package's release notes).
- [ ] CI runs on Node.js 22, 24 and 26.
