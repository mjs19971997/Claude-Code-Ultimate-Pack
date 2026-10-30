# Enforcing Architectural Boundaries with Tooling

Conventions erode unless a failing check protects them. Three kinds of check work well together: import-graph rules (dependency-cruiser, eslint-plugin-boundaries, ArchUnitTS or ArchUnit for the JVM), restricted-import lint rules for external packages, and the package manager or build system as a hard boundary. Versions verified in 2026-10: dependency-cruiser 18.7, eslint-plugin-boundaries 7.4, ArchUnitTS (`archunit` on npm, unaffiliated with the Java ArchUnit) expresses rules as tests and runs inside Jest, Vitest or Jasmine. The library's own matcher is `await expect(rule).toPassAsync()`; with Vitest it needs `globals: true` in `vitest.config.ts`. In a check with `archunit` 2.5 and Vitest 5 the matcher worked at runtime but `tsc` did not see its type, so the example below calls `rule.check()` (which returns the list of violations) and asserts on it, which type-checks and runs everywhere.

```typescript
// file: test/architecture.test.ts
import { projectFiles } from 'archunit';

const outerOfDomain = ['src/application/**', 'src/infrastructure/**', 'src/delivery/**'];
const outerOfApplication = ['src/infrastructure/**', 'src/delivery/**'];

describe('architecture', () => {
  it.each(outerOfDomain)('domain does not depend on %s', async (outer) => {
    const rule = projectFiles().inFolder('src/domain/**').shouldNot().dependOnFiles().inFolder(outer);
    expect(await rule.check()).toEqual([]);
  });

  it.each(outerOfApplication)('application does not depend on %s', async (outer) => {
    const rule = projectFiles().inFolder('src/application/**').shouldNot().dependOnFiles().inFolder(outer);
    expect(await rule.check()).toEqual([]);
  });

  it('has no circular dependencies', async () => {
    const rule = projectFiles().inFolder('src/**').should().haveNoCycles();
    expect(await rule.check()).toEqual([]);
  });
});
```

A rule whose folder pattern matches no files is reported as a violation ("Empty test"), which protects against typos in patterns; remove a rule when its folder does not exist yet, or pass `{ allowEmptyTests: true }` to `check`.

ArchUnitTS also offers code-metric rules (`metrics()`, for example `count().linesOfCode().shouldBeBelow(n)`). Treat any numeric limit as a project-chosen default to tune, not a universal rule.

## 5. Java and Kotlin: ArchUnit

ArchUnit (`com.tngtech.archunit:archunit` or `archunit-junit5`) evaluates rules against compiled classes. `layeredArchitecture()` states layers and who may access whom; `Architectures.onionArchitecture()` is also provided for onion-style layouts. Check the ArchUnit user guide for the current package names and examples before copying a rule.

```java
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

// inside a test that has a JavaClasses fixture:
layeredArchitecture().consideringAllDependencies()
    .layer("Domain").definedBy("..domain..")
    .layer("Application").definedBy("..application..")
    .layer("Infrastructure").definedBy("..infrastructure..")
    .whereLayer("Domain").mayNotAccessAnyLayer()
    .whereLayer("Application").mayOnlyAccessLayers("Domain")
    .whereLayer("Infrastructure").mayOnlyAccessLayers("Application", "Domain")
    .check(importedClasses);
```

## 6. Monorepo and package boundaries

- Make each layer or module a workspace package with its own `package.json`. A layer can only import what it lists in `dependencies`, and the package manager's strict mode (for example pnpm's non-flat `node_modules`) turns an undeclared import into a resolution error.
- Give each package an `exports` map so only the public entry point can be imported; deep imports then fail at runtime and in TypeScript with `moduleResolution` set to `node16`, `nodenext` or `bundler`.
- In Nx workspaces, `@nx/enforce-module-boundaries` checks project tags: each project is tagged (for example `layer:domain`) and `depConstraints` entries use `sourceTag` and `onlyDependOnLibsWithTags` to list what may be imported. See the Nx documentation for the current configuration file format.
- TypeScript project references (`composite`, `references`) prevent a package from importing source that is not in its references, and speed up incremental builds.

## 7. Adopting rules on an existing codebase

1. Draw the target layering and write the rules, then run them to count current violations.
2. Freeze the existing violations as a baseline so CI fails only on new ones: dependency-cruiser supports `--baseline` to write a known-violations file and `--ignore-known` to skip them (see `npx depcruise --help` for the current flags).
3. Treat the baseline file as a to-do list: each pull request that touches a violating file removes entries, and the baseline is only allowed to shrink.
4. Start with the highest-value rules: domain imports nothing outward, no cycles between modules, no deep imports into another module.
5. Mark intentional exceptions in the configuration with a comment and an owner, not with inline disable comments scattered through the code.
