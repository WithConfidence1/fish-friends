import SwiftUI
import WebKit

struct GameWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.userContentController.add(context.coordinator, name: "persist")

        if let saved = UserDefaults.standard.dictionary(forKey: "gameState") as? [String: String] {
            let names = ["progress": "tap-count-progress", "treasures": "tap-count-treasures",
                         "settings": "tap-count-settings", "backup": "tap-count-backup"]
            let js = saved.compactMap { key, value -> String? in
                guard let store = names[key],
                      let data = try? JSONSerialization.data(withJSONObject: value, options: .fragmentsAllowed),
                      let literal = String(data: data, encoding: .utf8) else { return nil }
                return "if (localStorage.getItem('\(store)') === null) localStorage.setItem('\(store)', \(literal));"
            }.joined(separator: "\n")
            config.userContentController.addUserScript(
                WKUserScript(source: js, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.bounces = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.allowsLinkPreview = false
        webView.allowsBackForwardNavigationGestures = false

        if let index = Bundle.main.url(forResource: "index",
                                       withExtension: "html",
                                       subdirectory: "web") {
            webView.loadFileURL(index,
                                allowingReadAccessTo: index.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.scrollView.pinchGestureRecognizer?.isEnabled = false
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        // The web view only ever shows the local game.
        func webView(_ webView: WKWebView,
                     decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            decisionHandler(navigationAction.request.url?.isFileURL == true ? .allow : .cancel)
        }

        // Mirrors the game's localStorage into UserDefaults so a purge/reinstall
        // can be recovered from via the boot-time seed script in makeUIView.
        func userContentController(_ userContentController: WKUserContentController,
                                    didReceive message: WKScriptMessage) {
            guard message.name == "persist",
                  let body = message.body as? [String: Any] else { return }
            let knownKeys = ["progress", "treasures", "settings", "backup"]
            var mirrored: [String: String] = [:]
            for key in knownKeys {
                if let value = body[key] as? String {
                    mirrored[key] = value
                }
            }
            UserDefaults.standard.set(mirrored, forKey: "gameState")
        }
    }
}
