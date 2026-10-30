# UIKit

UIKit-specific guidance for the swift-expert skill. UIKit view controllers, views and most delegate protocols are main-actor isolated in current SDKs, so UIKit code in Swift 6 mode runs on `@MainActor` by default. Examples target iOS 15+ unless noted.

## Lifecycle

- `loadView` creates a custom root view (no `super` call when you assign `view` yourself); `viewDidLoad` does one-time setup.
- `viewWillAppear` / `viewDidAppear` refresh visible data and start animations; `viewWillDisappear` / `viewDidDisappear` pause work and cancel tasks owned by the screen.
- `viewIsAppearing(_:)` (iOS 13+ via back-deployment in recent SDKs) runs when the view has its final traits and geometry; prefer it over `viewWillAppear` for geometry-dependent setup.
- Trait changes: register with `registerForTraitChanges(_:handler:)` (iOS 17+) instead of overriding the deprecated `traitCollectionDidChange(_:)`.
- `layoutSubviews` and `draw(_:)` run often; only set frames or draw there, never fetch data or create views.

## Auto Layout

- Use layout anchors and activate constraints in one batch with `NSLayoutConstraint.activate([...])`; set `translatesAutoresizingMaskIntoConstraints = false` on views you constrain.
- Pin content to `safeAreaLayoutGuide` or `layoutMarginsGuide`; use `keyboardLayoutGuide` (iOS 15+) to keep inputs above the keyboard.
- Resolve ambiguity with content hugging and compression resistance priorities rather than fixed sizes, so Dynamic Type can grow labels.
- `UIStackView` for linear layouts; nest sparingly in scrolling cells.

## Collection views with diffable data sources

Use `UICollectionViewCompositionalLayout` (list configuration for table-style screens), `UICollectionView.CellRegistration` and a diffable data source keyed by stable identifiers. Snapshots of identifiers plus `reconfigureItems` avoid reloading whole cells when content changes.

```swift
import UIKit

struct ArticleRow: Hashable, Sendable {
    let id: String
    let title: String
    let summary: String
}

final class ArticleListViewController: UIViewController {
    enum Section { case main }

    private var rows: [String: ArticleRow] = [:]
    private lazy var collectionView = UICollectionView(frame: .zero, collectionViewLayout: makeLayout())
    private lazy var dataSource = makeDataSource()
    var onSelect: ((String) -> Void)?

    override func viewDidLoad() {
        super.viewDidLoad()
        collectionView.translatesAutoresizingMaskIntoConstraints = false
        collectionView.delegate = self
        view.addSubview(collectionView)
        NSLayoutConstraint.activate([
            collectionView.topAnchor.constraint(equalTo: view.topAnchor),
            collectionView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            collectionView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            collectionView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
    }

    func show(_ newRows: [ArticleRow]) {
        let changed = newRows.filter { rows[$0.id] != nil && rows[$0.id] != $0 }.map(\.id)
        rows = Dictionary(uniqueKeysWithValues: newRows.map { ($0.id, $0) })

        var snapshot = NSDiffableDataSourceSnapshot<Section, String>()
        snapshot.appendSections([.main])
        snapshot.appendItems(newRows.map(\.id))
        snapshot.reconfigureItems(changed)
        dataSource.apply(snapshot, animatingDifferences: true)
    }

    private func makeLayout() -> UICollectionViewLayout {
        let configuration = UICollectionLayoutListConfiguration(appearance: .insetGrouped)
        return UICollectionViewCompositionalLayout.list(using: configuration)
    }

    private func makeDataSource() -> UICollectionViewDiffableDataSource<Section, String> {
        let registration = UICollectionView.CellRegistration<UICollectionViewListCell, String> { [weak self] cell, _, id in
            guard let row = self?.rows[id] else { return }
            var content = cell.defaultContentConfiguration()
            content.text = row.title
            content.secondaryText = row.summary
            content.secondaryTextProperties.numberOfLines = 2
            cell.contentConfiguration = content
            cell.accessories = [.disclosureIndicator()]
        }
        return UICollectionViewDiffableDataSource(collectionView: collectionView) { collectionView, indexPath, id in
            collectionView.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: id)
        }
    }
}

extension ArticleListViewController: UICollectionViewDelegate {
    func collectionView(_ collectionView: UICollectionView, didSelectItemAt indexPath: IndexPath) {
        guard let id = dataSource.itemIdentifier(for: indexPath) else { return }
        collectionView.deselectItem(at: indexPath, animated: true)
        onSelect?(id)
    }
}
```

- Apply snapshots from the main actor only; mixing queues corrupts the data source.
- `UIListContentConfiguration` scales with Dynamic Type automatically.
- `UIHostingConfiguration` (iOS 16+) renders SwiftUI content inside a cell: `cell.contentConfiguration = UIHostingConfiguration { RowView(row: row) }`.
- Custom cells reset transient state in `prepareForReuse()` and cancel image loads they started.

## Containment

```swift
extension UIViewController {
    func embed(_ child: UIViewController, in container: UIView) {
        addChild(child)
        child.view.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(child.view)
        NSLayoutConstraint.activate([
            child.view.topAnchor.constraint(equalTo: container.topAnchor),
            child.view.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            child.view.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            child.view.bottomAnchor.constraint(equalTo: container.bottomAnchor),
        ])
        child.didMove(toParent: self)
    }

    func removeFromContainer() {
        willMove(toParent: nil)
        view.removeFromSuperview()
        removeFromParent()
    }
}
```

Adding a child's view without `addChild` / `didMove(toParent:)` breaks appearance callbacks, trait propagation and rotation.

## Presentation and custom transitions

- Standard sheets: set `sheetPresentationController?.detents = [.medium(), .large()]` (iOS 15+) before presenting.
- `transitioningDelegate` is a **weak** property. Keep a strong reference to the delegate (for example a stored property on the presenter), or the custom transition silently falls back to the default.

```swift
import UIKit

final class SlideAnimator: NSObject, UIViewControllerAnimatedTransitioning {
    let isPresenting: Bool

    init(isPresenting: Bool) {
        self.isPresenting = isPresenting
    }

    func transitionDuration(using context: UIViewControllerContextTransitioning?) -> TimeInterval {
        UIAccessibility.isReduceMotionEnabled ? 0.2 : 0.35
    }

    func animateTransition(using context: UIViewControllerContextTransitioning) {
        let key: UITransitionContextViewKey = isPresenting ? .to : .from
        guard let movingView = context.view(forKey: key) else {
            context.completeTransition(false)
            return
        }
        let container = context.containerView
        let offscreen = container.bounds.offsetBy(dx: container.bounds.width, dy: 0)
        if isPresenting {
            movingView.frame = offscreen
            container.addSubview(movingView)
        }
        UIView.animate(withDuration: transitionDuration(using: context), delay: 0, options: [.curveEaseInOut]) {
            movingView.frame = self.isPresenting ? container.bounds : offscreen
        } completion: { _ in
            context.completeTransition(!context.transitionWasCancelled)
        }
    }
}

final class SlideTransitionDelegate: NSObject, UIViewControllerTransitioningDelegate {
    func animationController(forPresented presented: UIViewController,
                             presenting: UIViewController,
                             source: UIViewController) -> UIViewControllerAnimatedTransitioning? {
        SlideAnimator(isPresenting: true)
    }

    func animationController(forDismissed dismissed: UIViewController) -> UIViewControllerAnimatedTransitioning? {
        SlideAnimator(isPresenting: false)
    }
}

final class PresentingViewController: UIViewController {
    private let slideTransition = SlideTransitionDelegate()   // strong: transitioningDelegate is weak

    func showDetail(_ detail: UIViewController) {
        detail.modalPresentationStyle = .custom
        detail.transitioningDelegate = slideTransition
        present(detail, animated: true)
    }
}
```

Interactive dismissal adds `interactionControllerForDismissal(using:)` returning a `UIPercentDrivenInteractiveTransition` driven by a pan gesture.

## Images

Decode and downsample large images off the main actor; full-resolution decoding of camera photos costs tens of megabytes per image.

```swift
import ImageIO
import UIKit

@concurrent
func downsampledImage(at url: URL, maxPixelSize: CGFloat) async -> UIImage? {
    let sourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
    guard let source = CGImageSourceCreateWithURL(url as CFURL, sourceOptions) else { return nil }
    let thumbnailOptions = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxPixelSize,
    ] as CFDictionary
    guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0, thumbnailOptions) else { return nil }
    return UIImage(cgImage: image)
}
```

Pass `maxPixelSize` as the display size in points multiplied by the screen scale. `@concurrent` needs Swift 6.2 or later.

## Gestures and input

- Configure simultaneous recognition through `UIGestureRecognizerDelegate.gestureRecognizer(_:shouldRecognizeSimultaneouslyWith:)` and ordering with `require(toFail:)`.
- Prefer `UIAction`-based APIs (`UIButton(configuration:primaryAction:)`, `UIMenu`) over target-action selectors in new code.
- `UIButton.Configuration` (iOS 15+) handles styling, Dynamic Type and content insets.

## Accessibility

- Set `accessibilityLabel`, `accessibilityTraits` and `accessibilityValue` on custom controls; group composite views with `isAccessibilityElement` on the container or `accessibilityElements` ordering.
- Fonts: `UIFont.preferredFont(forTextStyle:)` with `adjustsFontForContentSizeCategory = true`, or `UIFontMetrics` for custom fonts.
- Check `UIAccessibility.isReduceMotionEnabled` and observe its change notification for animations.

## SwiftUI interop

- Host SwiftUI in UIKit with `UIHostingController(rootView:)` (add as a child view controller) or `UIHostingConfiguration` in cells.
- Wrap UIKit views for SwiftUI with `UIViewRepresentable`; use a `Coordinator` for delegates and keep `updateUIView` idempotent.

## Memory and performance

- Delegates and parent references are `weak`; escaping closures stored by a view controller capture `[weak self]`.
- Avoid `shouldRasterize` unless Instruments shows a win; offscreen rendering from masks and shadows without `shadowPath` is a common frame-drop cause.
- Use prefetching (`UICollectionViewDataSourcePrefetching`) to start image loads early and cancel them in `cancelPrefetchingForItemsAt`.
- Profile scrolling with the Animation Hitches and Time Profiler instruments.

## Common mistakes

- Force-casting dequeued cells (`as! MyCell`); cell registrations make this unnecessary.
- `reloadData()` after every change: loses animations and selection; apply snapshots instead.
- A local `let delegate = SlideTransitionDelegate()` assigned to `transitioningDelegate`: it deallocates immediately.
- Doing network calls in `layoutSubviews` or cell configuration without cancellation on reuse.
- Hard-coded font sizes that ignore Dynamic Type.
