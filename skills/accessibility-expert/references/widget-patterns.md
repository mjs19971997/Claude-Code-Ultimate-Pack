# Widget Patterns

Keyboard models and minimal implementations for common custom widgets. They follow the WAI-ARIA Authoring Practices Guide (APG). Before building any of these by hand, check whether a native element (`<select>`, `<details>`, `<dialog>`, `popover`) or a maintained library (React Aria, Radix UI) already covers the need. Verified against the WAI-ARIA Authoring Practices Guide, WAI-ARIA 1.2 and React 18+ hooks (2026-10).

## 1. Keyboard models

| Widget | Tab | Arrow keys | Other keys |
|---|---|---|---|
| Tabs | Moves into the active tab, then into the panel | Left/Right (or Up/Down if vertical) move between tabs | Home/End: first/last tab |
| Menu button + menu | Focuses the button | Down/Up move through items once open | Enter/Space activate; Escape closes and returns focus to the button |
| Disclosure | Focuses the button | none | Enter/Space toggle |
| Radio group | One stop for the group | Arrows move and select | Space selects the focused radio |
| Listbox | One stop | Up/Down move | Home/End; type-ahead; Shift+arrows for multi-select |
| Combobox | Focuses the input | Down opens and moves into the list | Escape closes; Enter accepts |
| Dialog | Cycles inside the dialog | none | Escape closes |

"Menu" roles (`menu`, `menuitem`) are for application-style menus. A site navigation list is a `<nav>` with links, not a `role="menu"`.

## 2. Tabs with roving tabindex

```tsx
// src/components/ui/tabs.tsx
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

export function Tabs({ tabs, label }: { tabs: Tab[]; label: string }) {
  const [active, setActive] = useState(0);
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const baseId = useId();

  function focusTab(index: number) {
    const next = (index + tabs.length) % tabs.length;
    setActive(next);
    refs.current[next]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    switch (event.key) {
      case 'ArrowRight': focusTab(active + 1); break;
      case 'ArrowLeft': focusTab(active - 1); break;
      case 'Home': focusTab(0); break;
      case 'End': focusTab(tabs.length - 1); break;
      default: return;
    }
    event.preventDefault();
  }

  return (
    <div>
      <div role="tablist" aria-label={label}>
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            ref={(el) => { refs.current[i] = el; }}
            type="button"
            role="tab"
            id={`${baseId}-tab-${tab.id}`}
            aria-selected={i === active}
            aria-controls={`${baseId}-panel-${tab.id}`}
            tabIndex={i === active ? 0 : -1}
            onClick={() => setActive(i)}
            onKeyDown={onKeyDown}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${baseId}-panel-${tab.id}`}
          aria-labelledby={`${baseId}-tab-${tab.id}`}
          tabIndex={0}
          hidden={i !== active}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
```

This uses automatic activation (arrow keys select). If showing a panel is expensive, use manual activation: arrows move focus only, Enter/Space select.

## 3. Disclosure

```tsx
// src/components/ui/disclosure.tsx
import { useId, useState, type ReactNode } from 'react';

export function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div>
      <button type="button" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
        {summary}
      </button>
      <div id={panelId} hidden={!open}>
        {children}
      </div>
    </div>
  );
}
```

For static content, `<details><summary>…</summary>…</details>` needs no script at all.

## 4. App-wide announcements

```tsx
// src/components/live-region.tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

const AnnounceContext = createContext<(message: string) => void>(() => {});

export function LiveRegionProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  const announce = useCallback((text: string) => {
    setMessage('');                                       // clear so a repeated message is re-announced
    requestAnimationFrame(() => setMessage(text));
  }, []);
  return (
    <AnnounceContext.Provider value={announce}>
      {children}
      <div role="status" aria-live="polite" className="visually-hidden">
        {message}
      </div>
    </AnnounceContext.Provider>
  );
}

export const useAnnounce = () => useContext(AnnounceContext);
```

The region is rendered on first load and stays mounted; only its text changes.

## 5. Visually hidden utility

```css
/* src/styles/base.css */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

The global reduced-motion override is a safety net; components should still choose a calmer alternative (fade instead of slide) rather than relying on it alone.

## 6. Combobox notes

A combobox (autocomplete) is the widget most often broken by hand-rolled code. Requirements include `role="combobox"` on the input, `aria-expanded`, `aria-controls` pointing to a `role="listbox"`, `aria-activedescendant` for the highlighted option, and a polite announcement of the result count. Prefer a library that implements the APG combobox pattern and test it with at least two screen readers.
