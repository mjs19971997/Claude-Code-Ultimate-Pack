# Ownership, Borrowing and Lifetimes

Working notes for the borrow checker: how moves and borrows work, when lifetimes must be written, how to restructure code instead of cloning, and which temporary and capture rules changed in the 2024 edition. Verified against Rust 1.99.1, edition 2024 (2026-10).

## Contents

1. [Ownership and moves](#1-ownership-and-moves)
2. [Borrowing rules](#2-borrowing-rules)
3. [Lifetime elision and annotations](#3-lifetime-elision-and-annotations)
4. [Structs that borrow](#4-structs-that-borrow)
5. [Cow and smart pointers](#5-cow-and-smart-pointers)
6. [Edition 2024 scope and capture rules](#6-edition-2024-scope-and-capture-rules)
7. [Reading borrow errors](#7-reading-borrow-errors)

## 1. Ownership and moves

- Each value has one owner. Assigning, passing by value or returning moves the value; the old binding is unusable (E0382, "borrow of moved value").
- `Copy` types (integers, `bool`, `char`, shared references, tuples of `Copy`) are copied instead of moved. Derive `Copy` only for small plain data.
- `Clone` is an explicit, possibly expensive duplicate. Prefer a borrow; clone at a boundary where independent ownership is the point (sending to another thread, storing in a cache).
- `std::mem::take(&mut x)` replaces with `Default` and returns the old value; `mem::replace(&mut x, new)` and `Option::take()` do the same for state machines and linked structures without cloning.
- Closures capture by reference, by mutable reference or by move depending on use; add `move` when the closure must own its captures (threads, `tokio::spawn`).

```rust
use std::mem;

pub fn drain(v: &mut Vec<u8>) -> Vec<u8> {
    mem::take(v)
}

pub fn names(users: &[(u32, String)]) -> Vec<&str> {
    users.iter().map(|(_, n)| n.as_str()).collect()
}
```

## 2. Borrowing rules

- At any time a value has either any number of shared borrows (`&T`) or exactly one mutable borrow (`&mut T`), never both. The borrow lasts until its last use, not until the end of the block (non-lexical lifetimes).
- E0499 (two mutable borrows) and E0502 (mutable while shared) usually mean one borrow is held longer than needed. End it earlier by finishing the use, copying out a small value, or collecting first.
- Disjoint fields can be borrowed together when the borrow is visible to the compiler (direct field access or destructuring), but not through methods that take `&mut self`.
- Use the `entry` API for get-or-insert instead of a lookup followed by an insert.
- Index into a `Vec` while mutating it is a common conflict; iterate with `iter_mut`, use `retain`, `drain`, or collect indices first.

```rust
use std::collections::HashMap;

pub fn count(map: &mut HashMap<String, u32>, key: &str) {
    *map.entry(key.to_owned()).or_insert(0) += 1;
}

pub struct Pair {
    a: Vec<u8>,
    b: Vec<u8>,
}

impl Pair {
    /// Destructuring splits the borrow of `self` into two disjoint field borrows.
    pub fn move_all(&mut self) {
        let Pair { a, b } = self;
        b.append(a);
    }
}
```

## 3. Lifetime elision and annotations

- A lifetime names how long a reference is valid; it never extends how long data lives. It only lets the compiler check relations between references.
- Elision rules for functions: each elided input lifetime becomes its own parameter; if there is exactly one input lifetime it is given to all outputs; if one input is `&self` or `&mut self`, its lifetime is given to all outputs. When none applies, write the lifetime (E0106, "missing lifetime specifier").
- `'static` as a bound (`T: 'static`) means the type holds no non-static borrows; it does not mean the value lives forever. `tokio::spawn` needs `'static` futures for this reason, so move owned data or `Arc` clones in.
- Higher-ranked bounds (`for<'a> Fn(&'a str) -> &'a str`) are needed when a closure must accept references of any lifetime; plain `Fn(&str) -> &str` usually elides to this form.

```rust
pub fn first_word(s: &str) -> &str {
    s.split_whitespace().next().unwrap_or("")
}

pub fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

pub fn apply<F>(f: F) -> usize
where
    F: for<'a> Fn(&'a str) -> &'a str,
{
    f("abc def").len()
}
```

## 4. Structs that borrow

- A struct holding a reference needs a lifetime parameter. Use it when the struct is a short-lived view (parser, iterator, request wrapper); store owned data (`String`, `Vec`, `Arc<str>`) in long-lived types.
- Returning pieces of the input from methods should use the struct's lifetime (`&'src str`), not the lifetime of `&mut self`; otherwise the caller cannot keep two tokens at once.
- Self-referential structs (a field borrowing another field) are not expressible in safe Rust. Store indices or ranges, use an arena, or restructure into two types.

```rust
pub struct Parser<'src> {
    input: &'src str,
    pos: usize,
}

impl<'src> Parser<'src> {
    pub fn new(input: &'src str) -> Self {
        Self { input, pos: 0 }
    }

    /// Tokens borrow from the input (`'src`), not from the parser.
    pub fn next_token(&mut self) -> Option<&'src str> {
        let rest = &self.input[self.pos..];
        let trimmed = rest.trim_start();
        if trimmed.is_empty() {
            return None;
        }
        let start = self.pos + (rest.len() - trimmed.len());
        let end = trimmed
            .find(char::is_whitespace)
            .map_or(self.input.len(), |i| start + i);
        self.pos = end;
        Some(&self.input[start..end])
    }
}
```

## 5. Cow and smart pointers

| Type | Use | Cost or limit |
|---|---|---|
| `Box<T>` | Heap allocation, recursive types, `Box<dyn Trait>` | One allocation; single owner |
| `Rc<T>` | Shared ownership on one thread | Not `Send`; cycles leak (use `Weak`) |
| `Arc<T>` | Shared ownership across threads, shared immutable config | Atomic refcount; cycles leak |
| `Cell<T>` / `RefCell<T>` | Interior mutability on one thread | `RefCell` panics on a borrow conflict at runtime |
| `Mutex<T>` / `RwLock<T>` | Interior mutability across threads | Lock contention; poisoning on panic; do not hold across `.await` |
| `OnceLock<T>` / `LazyLock<T>` | Lazy global or one-time init | Initialization runs once; keep the closure cheap and non-blocking |
| `Cow<'a, B>` | Borrow when unchanged, own when changed | Extra branch and lifetime parameter |

```rust
use std::borrow::Cow;

pub fn normalize(s: &str) -> Cow<'_, str> {
    if s.contains('\t') {
        Cow::Owned(s.replace('\t', " "))
    } else {
        Cow::Borrowed(s)
    }
}
```

- Use `Arc<str>` or `Arc<[T]>` for cheap-to-clone immutable text and lists.
- `Rc<RefCell<T>>` and `Arc<Mutex<T>>` are a sign to ask whether a message-passing design or an arena with indices would be simpler.
- Break cycles with `Weak<T>`; parent pointers in trees are the usual case.

## 6. Edition 2024 scope and capture rules

- Tail-expression temporaries: temporaries created in the final expression of a block or function body are dropped before the block's local variables. Code such as `let c = RefCell::new(".."); c.borrow().len()` compiles in 2024; in 2021 it fails with E0597. Code that relied on the old order (a temporary guard outliving a local) may need a `let` binding to keep the guard alive.
- `if let` rescope: temporaries from the scrutinee are dropped before the `else` branch runs. A read lock taken in `if let Some(x) = *lock.read().unwrap()` is released before `else`, so the `else` branch can take the write lock without deadlocking.
- Return-position `impl Trait` captures every in-scope generic and lifetime parameter by default. `fn evens(v: &[u32]) -> impl Iterator<Item = &u32>` and code like `fn f(v: &[u32]) -> impl Iterator<Item = u32>` (which borrows `v`) work without `+ '_` or a `Captures` trick. To say the result does not borrow, write `+ use<>`; to list captures, `+ use<'a, T>`.
- `let` chains are available in `if` and `while`; the `let` expressions must be joined by `&&` at the top level.
- `static mut`: taking `&X` or `&mut X` is denied by `static_mut_refs`. Use `&raw const X` / `&raw mut X`, or better, atomics, `Mutex` or `OnceLock`.
- `Box<[T]>` now implements `IntoIterator` by value in 2024 (`boxed.into_iter()` yields `T`).

```rust
use std::cell::RefCell;
use std::sync::RwLock;

pub fn tail() -> usize {
    let c = RefCell::new("..");
    c.borrow().len() // compiles in edition 2024
}

pub fn ensure_set(value: &RwLock<Option<bool>>) {
    if let Some(x) = *value.read().unwrap() {
        println!("value is {x}");
    } else {
        // 2024: the read guard is already dropped here.
        *value.write().unwrap() = Some(true);
    }
}

pub fn evens(v: &[u32]) -> impl Iterator<Item = &u32> {
    v.iter().filter(|x| **x % 2 == 0)
}

pub fn repeated_sum(v: &[u32]) -> impl Iterator<Item = u32> + use<> {
    let sum: u32 = v.iter().sum();
    std::iter::repeat_n(sum, 3) // does not borrow `v`
}
```

## 7. Reading borrow errors

| Error | Meaning | Typical fix |
|---|---|---|
| E0382 borrow of moved value | The value was moved earlier | Borrow instead, clone at a boundary, or restructure so the move is the last use |
| E0499 two mutable borrows | Overlapping `&mut` | End the first borrow earlier, split fields, use indices |
| E0502 mutable and shared borrow | A `&` is alive while mutating | Copy out the needed value, collect first, or reorder |
| E0505 move out while borrowed | Moving a value that has a live borrow | Drop the borrow first or clone the needed part |
| E0506 assign to borrowed value | Writing while a reference is alive | Finish using the reference before assignment |
| E0597 does not live long enough | A reference outlives its owner | Return owned data, extend the owner's scope, or use the 2024 tail rules |
| E0106 missing lifetime specifier | Elision cannot decide | Add a named lifetime that relates inputs and output |
| E0373 closure may outlive function | A thread or task closure borrows a local | Use `move` and give the closure owned data or an `Arc` |
| E0507 cannot move out of borrow | Moving a field out of `&` or index | `clone`, `mem::take`, `Option::take`, or pattern with `ref` |

- Read the labels in the message: they mark where the borrow starts, where it is used later and where the conflicting use happens.
- Fix the structure first. A `clone()` or `Rc<RefCell<_>>` added only to stop the error usually moves the problem to runtime.
- `rustc --explain E0502` prints a long description with examples for any error code.
