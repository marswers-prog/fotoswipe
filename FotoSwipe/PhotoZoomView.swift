import SwiftUI
import Photos
import UIKit

struct PhotoZoomSelection: Identifiable {
    let asset: PHAsset
    let preview: UIImage?
    var id: String { asset.localIdentifier }
}

struct PhotoZoomView: View {
    let asset: PHAsset
    let preview: UIImage?
    @Environment(\.dismiss) private var dismiss
    @State private var image: UIImage?
    @State private var loading = true
    @State private var loadFailed = false
    @State private var token = UUID()
    @State private var requestID: PHImageRequestID = PHInvalidImageRequestID

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text(asset.creationDate?.formatted(date: .abbreviated, time: .omitted) ?? "Foto")
                    .font(.subheadline).foregroundStyle(.secondary)
                Spacer()
                Button("Schließen", systemImage: "xmark") { dismiss() }
                    .font(.subheadline.bold()).padding(.vertical, 8)
            }.padding(.horizontal, 20)
            ZStack {
                if let shownImage = image ?? preview {
                    PhotoZoomCanvas(image: shownImage)
                } else if loading {
                    ProgressView("Foto wird geladen …")
                }
                if loadFailed && image == nil && preview == nil {
                    VStack(spacing: 12) {
                        Image(systemName: "icloud.slash").font(.largeTitle)
                        Text("Foto konnte nicht geladen werden.")
                        Button("Erneut laden") { load() }
                    }
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
            VStack(spacing: 6) {
                Text("Mit zwei Fingern zoomen · Doppeltippen zum Vergrößern oder Zurücksetzen")
                    .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                if loading {
                    ProgressView("Mehr Details werden geladen …").font(.caption)
                } else if loadFailed {
                    Button("Mehr Details erneut laden") { load() }.font(.caption)
                }
            }.padding(.horizontal, 20).padding(.bottom, 12)
        }
        .padding(.top, 8).background(Color.black.ignoresSafeArea())
        .preferredColorScheme(.dark)
        .onAppear { load() }
        .onDisappear {
            token = UUID()
            PHImageManager.default().cancelImageRequest(requestID)
        }
    }

    private func load() {
        PHImageManager.default().cancelImageRequest(requestID)
        let generation = UUID()
        token = generation
        loading = true; loadFailed = false
        let options = PHImageRequestOptions()
        options.isNetworkAccessAllowed = true
        options.deliveryMode = .highQualityFormat
        options.resizeMode = .exact
        // Load more detail only in this view; bound memory for very large photos.
        let longest = max(asset.pixelWidth, asset.pixelHeight)
        let factor = min(1.0, 4096.0 / Double(max(longest, 1)))
        let target = CGSize(width: Double(asset.pixelWidth) * factor, height: Double(asset.pixelHeight) * factor)
        requestID = PHImageManager.default().requestImage(for: asset, targetSize: target, contentMode: .aspectFit, options: options) { result, info in
            let cancelled = (info?[PHImageCancelledKey] as? Bool) == true
            let degraded = (info?[PHImageResultIsDegradedKey] as? Bool) == true
            Task { @MainActor in
                guard token == generation, !cancelled else { return }
                if let result { image = result }
                if !degraded {
                    loading = false
                    loadFailed = result == nil
                }
            }
        }
    }
}

private struct PhotoZoomCanvas: UIViewRepresentable {
    let image: UIImage
    func makeUIView(context: Context) -> ZoomingImageScrollView { ZoomingImageScrollView(frame: .zero) }
    func updateUIView(_ uiView: ZoomingImageScrollView, context: Context) { uiView.display(image) }
}

private final class ZoomingImageScrollView: UIScrollView, UIScrollViewDelegate {
    private let photoView = UIImageView()
    private var viewport = CGSize.zero
    private var needsFit = true
    private var relativeZoom: CGFloat = 1
    private var focus = CGPoint(x: 0.5, y: 0.5)

    override init(frame: CGRect) {
        super.init(frame: frame)
        delegate = self
        backgroundColor = .black
        contentInsetAdjustmentBehavior = .never
        showsVerticalScrollIndicator = false
        showsHorizontalScrollIndicator = false
        bouncesZoom = true
        photoView.contentMode = .scaleAspectFit
        photoView.isAccessibilityElement = true
        photoView.accessibilityLabel = "Foto in Vollbild. Mit zwei Fingern zoomen."
        addSubview(photoView)
        let doubleTap = UITapGestureRecognizer(target: self, action: #selector(toggleZoom(_:)))
        doubleTap.numberOfTapsRequired = 2
        addGestureRecognizer(doubleTap)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    func display(_ image: UIImage) {
        guard photoView.image !== image else { return }
        rememberFocus()
        photoView.image = image
        needsFit = true
        setNeedsLayout()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard bounds.width > 0, bounds.height > 0, let image = photoView.image else { return }
        if viewport != bounds.size || needsFit {
            if !needsFit { rememberFocus() }
            viewport = bounds.size
            needsFit = false
            minimumZoomScale = 0.0001
            maximumZoomScale = 100
            setZoomScale(1, animated: false)
            photoView.frame = CGRect(origin: .zero, size: image.size)
            contentSize = image.size
            let fitted = min(bounds.width / max(image.size.width, 1), bounds.height / max(image.size.height, 1))
            maximumZoomScale = fitted * 8
            minimumZoomScale = fitted
            setZoomScale(min(maximumZoomScale, fitted * max(relativeZoom, 1)), animated: false)
            centerPhoto()
            let point = photoView.convert(CGPoint(x: focus.x * image.size.width, y: focus.y * image.size.height), to: self)
            let x = min(max(point.x - bounds.width / 2, -contentInset.left), max(-contentInset.left, contentSize.width - bounds.width + contentInset.right))
            let y = min(max(point.y - bounds.height / 2, -contentInset.top), max(-contentInset.top, contentSize.height - bounds.height + contentInset.bottom))
            setContentOffset(CGPoint(x: x, y: y), animated: false)
        }
    }

    private func rememberFocus() {
        guard photoView.image != nil, photoView.bounds.width > 0, photoView.bounds.height > 0 else { return }
        relativeZoom = zoomScale / max(minimumZoomScale, 0.0001)
        let point = photoView.convert(CGPoint(x: bounds.midX, y: bounds.midY), from: self)
        focus = CGPoint(x: min(max(point.x / photoView.bounds.width, 0), 1), y: min(max(point.y / photoView.bounds.height, 0), 1))
    }

    func viewForZooming(in scrollView: UIScrollView) -> UIView? { photoView }
    func scrollViewDidZoom(_ scrollView: UIScrollView) { centerPhoto() }

    private func centerPhoto() {
        let horizontal = max(0, (bounds.width - contentSize.width) / 2)
        let vertical = max(0, (bounds.height - contentSize.height) / 2)
        let next = UIEdgeInsets(top: vertical, left: horizontal, bottom: vertical, right: horizontal)
        if contentInset != next { contentInset = next }
    }

    @objc private func toggleZoom(_ gesture: UITapGestureRecognizer) {
        if zoomScale > minimumZoomScale * 1.05 {
            setZoomScale(minimumZoomScale, animated: true)
        } else {
            let scale = min(maximumZoomScale, minimumZoomScale * 3)
            let point = gesture.location(in: photoView)
            let rect = CGRect(x: point.x - bounds.width / scale / 2, y: point.y - bounds.height / scale / 2,
                              width: bounds.width / scale, height: bounds.height / scale)
            zoom(to: rect, animated: true)
        }
    }
}
