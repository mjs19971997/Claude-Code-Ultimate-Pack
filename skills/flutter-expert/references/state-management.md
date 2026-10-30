# State Management: Riverpod and Bloc

Reference for Riverpod 3 (flutter_riverpod 3.4.3, riverpod_generator 4.0.9) and flutter_bloc 9.1.1 with Dart 3.13 (2026-10). Open this file when choosing between the two, writing providers or blocs, migrating from Riverpod 2, or testing state logic.

## Contents

1. [Choosing a state tool](#1-choosing-a-state-tool)
2. [Riverpod providers](#2-riverpod-providers)
3. [Notifier and AsyncNotifier](#3-notifier-and-asyncnotifier)
4. [Code generation](#4-code-generation)
5. [Riverpod 3 migration notes](#5-riverpod-3-migration-notes)
6. [Bloc and Cubit](#6-bloc-and-cubit)
7. [Testing state](#7-testing-state)

## 1. Choosing a state tool

| Need | Choice |
|---|---|
| State local to one widget | `StatefulWidget`, `ValueNotifier` with `ValueListenableBuilder` |
| Shared state, dependency injection, caching of async data | Riverpod |
| Strict event to state mapping, audit trail of events, large teams used to the pattern | Bloc |
| Simple shared state with explicit methods and no providers | Cubit |

Keep one primary tool per app. Mixing is possible (a Bloc exposed through a provider), but each extra tool is a second set of rules to learn and test.

## 2. Riverpod providers

Wrap the app once: `runApp(const ProviderScope(child: MyApp()));`. Providers are global declarations that hold no state themselves; state lives in the `ProviderScope`.

| Provider | Use |
|---|---|
| `Provider<T>` | Dependencies and derived values (repositories, clients, computed data) |
| `FutureProvider<T>` / `StreamProvider<T>` | Read-only async values without methods |
| `NotifierProvider` | Synchronous state with methods |
| `AsyncNotifierProvider` | Async state with methods (load, then mutate) |
| `StreamNotifierProvider` | Stream-backed state with methods |

Reading rules:

- `ref.watch(p)` inside `build` or another provider: rebuilds when `p` changes.
- `ref.read(p)` inside callbacks and `onPressed`: one-time read, never in `build`.
- `ref.listen(p, (prev, next) {...})` for side effects such as snackbars and navigation.
- `ref.watch(p.select((s) => s.count))` to rebuild only when a slice changes.
- `ref.invalidate(p)` resets a provider; `ref.refresh(p)` resets and returns the new value.
- `ref.mounted` (and `Ref.mounted` in notifiers) tells whether the provider has been disposed, which guards writes after an `await`.

Widgets: `ConsumerWidget` (stateless), `ConsumerStatefulWidget` with `ConsumerState`, or `Consumer` for a small subtree. With `hooks_riverpod` you combine them with `flutter_hooks`.

Family and scoping: `Provider.family<T, Arg>((ref, arg) => ...)` creates one instance per argument; the argument needs a stable `==`. Override a provider for a subtree with a nested `ProviderScope(overrides: [...])`.

Auto dispose: providers created without code generation are kept alive by default unless declared with `isAutoDispose: true` (for example `Provider(isAutoDispose: true, ...)`). Generated providers are auto-dispose by default; use `@Riverpod(keepAlive: true)` to keep them.

## 3. Notifier and AsyncNotifier

```dart
class CartNotifier extends Notifier<List<Item>> {
  @override
  List<Item> build() => const [];

  void add(Item item) => state = [...state, item];
  void remove(String id) => state = [
    for (final i in state)
      if (i.id != id) i,
  ];
}

final cartProvider = NotifierProvider<CartNotifier, List<Item>>(CartNotifier.new);
```

- `build()` runs on first read and every time a watched dependency changes. The notifier is recreated on rebuild in Riverpod 3.
- Always assign a new immutable value to `state`; providers filter updates with `==`, so mutating a list in place is not noticed.
- Inside notifier methods use `ref.read` for other providers and `ref.watch` only in `build`.

Async state:

```dart
class ProfileNotifier extends AsyncNotifier<Profile> {
  @override
  Future<Profile> build() => ref.watch(profileRepositoryProvider).load();

  Future<void> rename(String name) async {
    final repo = ref.read(profileRepositoryProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => repo.rename(name));
  }
}
```

- `AsyncValue.guard` turns thrown errors into `AsyncError` so the UI can render them.
- Pattern match in the UI: `switch (value) { AsyncData(:final value) => ..., AsyncError(:final error) => ..., _ => loading }`.
- `AsyncValue.value` is nullable and null while loading or on error; `requireValue` throws instead.
- Failing providers retry automatically with a delay in Riverpod 3. Customize with the `retry` parameter on `ProviderScope`, `ProviderContainer` or a single provider; return `null` from the callback to stop retrying (useful for 4xx errors and in tests).
- Mutations (`Mutation` objects for tracking button-triggered side effects) are an experimental API in Riverpod 3 (`package:riverpod/experimental/`); prefer notifier methods unless the docs mark them stable.

## 4. Code generation

Add `riverpod_annotation`, and as dev dependencies `riverpod_generator` and `build_runner`. Then:

```dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'counter.g.dart';

@riverpod
class Counter extends _$Counter {
  @override
  int build() => 0;

  void increment() => state++;
}

@riverpod
Future<String> greeting(Ref ref) async => 'hello';
```

- Run `dart run build_runner build` once, or `dart run build_runner watch` while editing.
- The generated names are `counterProvider` and `greetingProvider`; family arguments become ordinary function or `build` parameters.
- Plain functions produce read-only providers; classes produce Notifier-style providers.
- Generation is optional. Pick it for ergonomic families and fewer provider types, skip it to avoid build times and generated files in review.
- `riverpod_lint` (3.1.9 at the time of writing) adds analyzer rules for provider misuse; check its README for the current setup steps.

## 5. Riverpod 3 migration notes

Summary of breaking changes from the package changelog (3.0.0):

- `StateProvider`, `StateNotifierProvider` and `ChangeNotifierProvider` moved to `package:flutter_riverpod/legacy.dart`. Migrate to `NotifierProvider`.
- `AutoDisposeNotifier`, `FamilyNotifier` and variants are merged into `Notifier`; `Ref` subclasses such as `FutureProviderRef` are removed, use `Ref`.
- `AsyncValue.valueOrNull` is removed; `AsyncValue.value` now returns null during errors.
- All providers use `==` to filter updates; override `updateShouldNotify` in a Notifier for the old behaviour.
- Using a ref or notifier after disposal throws, except for `mounted`.
- Errors rethrown by `ref.watch`/`ref.read` are wrapped in `ProviderException`.
- `ProviderObserver` methods take a `ProviderObserverContext`.
- `StreamProvider` pauses its subscription when the provider is not actively listened.
- Providers and notifiers are paused when all listeners are paused (for example, widgets in an offstage tab).

Read the official "What's new in Riverpod 3.0" page on riverpod.dev for the full list and migration steps.

## 6. Bloc and Cubit

A `Cubit<S>` exposes methods that call `emit(newState)`. A `Bloc<E, S>` receives events and registers handlers with `on<Event>`.

```dart
import 'package:bloc_concurrency/bloc_concurrency.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

sealed class SearchEvent {
  const SearchEvent();
}

final class QueryChanged extends SearchEvent {
  const QueryChanged(this.query);
  final String query;
}

sealed class SearchState extends Equatable {
  const SearchState();
  @override
  List<Object?> get props => [];
}

final class SearchIdle extends SearchState {
  const SearchIdle();
}

final class SearchLoaded extends SearchState {
  const SearchLoaded(this.results);
  final List<String> results;
  @override
  List<Object?> get props => [results];
}

final class SearchFailed extends SearchState {
  const SearchFailed();
}

class SearchBloc extends Bloc<SearchEvent, SearchState> {
  SearchBloc(this._search) : super(const SearchIdle()) {
    on<QueryChanged>(_onQuery, transformer: restartable());
  }

  final Future<List<String>> Function(String) _search;

  Future<void> _onQuery(QueryChanged event, Emitter<SearchState> emit) async {
    try {
      emit(SearchLoaded(await _search(event.query)));
    } on Exception {
      emit(const SearchFailed());
    }
  }
}
```

Widget side:

- `BlocProvider(create: (_) => SearchBloc(...), child: ...)` creates and closes the bloc; `BlocProvider.value` only supplies an existing instance and does not close it.
- `BlocBuilder<B, S>` rebuilds the UI; `buildWhen` narrows rebuilds. `BlocSelector` picks a slice.
- `BlocListener` runs side effects once per state change (navigation, snackbars); `BlocConsumer` combines both.
- `context.read<B>()` in callbacks, `context.watch<B>()` in `build`, `context.select` for slices.
- `restartable()`, `droppable()`, `sequential()` and `concurrent()` come from `bloc_concurrency`; use `restartable()` for search-as-you-type and `droppable()` for submit buttons. Add a debounce with a custom transformer when needed.
- States need value equality (Equatable, or records, or freezed classes) because Bloc skips emissions equal to the current state.
- Never emit after the handler's `emit` is done; make handlers `async` and `await` the work so `emit` stays valid.

## 7. Testing state

Riverpod:

- Widget tests: `ProviderScope(overrides: [repoProvider.overrideWithValue(fake)], child: ...)`.
- Unit tests: create `ProviderContainer.test(overrides: [...])` (Riverpod 3), read the provider, and `await container.read(p.future)` for async providers; the container is disposed automatically after the test.
- Mock only the notifier's `build` with `provider.overrideWithBuild(...)` when you want the real methods.
- Pass `retry: (_, _) => null` to the container or scope when the test expects an error.

Bloc:

```dart
test('emits loaded results', () async {
  final bloc = SearchBloc((q) async => [q]);
  addTearDown(bloc.close);

  final expectation = expectLater(
    bloc.stream,
    emitsInOrder([const SearchLoaded(['dart'])]),
  );
  bloc.add(const QueryChanged('dart'));
  await expectation;
});
```

- Register the stream expectation before adding the event so no emission is missed.
- `bloc_test` provides `blocTest` and `MockBloc`; check that it resolves against the SDK before depending on it, since it pins `test` packages that Flutter also pins.
- Widget tests with Bloc: provide a mock or real bloc with `BlocProvider.value`, pump, then assert on `find` results.
