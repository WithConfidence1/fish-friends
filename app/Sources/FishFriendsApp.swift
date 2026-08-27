import SwiftUI
import AVFoundation

@main
struct FishFriendsApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        // Audible even with the mute switch on, per spec.
        try? AVAudioSession.sharedInstance().setCategory(.playback)
        try? AVAudioSession.sharedInstance().setActive(true)
    }

    var body: some Scene {
        WindowGroup {
            GameWebView()
                .ignoresSafeArea()
                .background(Color.black)
                .statusBarHidden(true)
                .persistentSystemOverlays(.hidden)
        }
        .onChange(of: scenePhase) { phase in
            // Wake lock only while the aquarium is actually up.
            UIApplication.shared.isIdleTimerDisabled = (phase == .active)
        }
    }
}
