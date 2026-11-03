import Foundation

func check(_ condition: @autoclosure () -> Bool, _ explanation: String) {
    guard condition() else { fatalError(explanation) }
}

let suite = "FotoSwipeTests-\(UUID().uuidString)"
let defaults = UserDefaults(suiteName: suite)!
defer { defaults.removePersistentDomain(forName: suite) }

// Realistic migration fixture: more than 2,000 reviews from the installed app.
let legacy = Set((0..<2307).map { "legacy-photo-\($0)" })
defaults.set(Array(legacy), forKey: "reviewed")
defaults.set("upper-existing-album", forKey: "upAlbum")
defaults.set("lower-existing-album", forKey: "downAlbum")
var state = try ReviewState(defaults: defaults)
check(state.reviewed == legacy, "Migration must preserve every existing review")
check(state.pending.isEmpty, "Migration must not stage existing photos for deletion")
check(!state.shouldShow("legacy-photo-42"), "An old review must stay skipped")

state.stageDeletion("new-A")
state.stageDeletion("new-B")
state.stageDeletion("new-A")
check(state.pending == ["new-A", "new-B"], "Queue must preserve order without duplicates")
check(!state.shouldShow("new-A"), "Staged photos must immediately leave the swipe deck")
check(!state.reviewed.contains("new-A"), "Staging must not claim a successful deletion")
try state.save(to: defaults)

// Reload after closing the app, or after a cancelled/failed deletion with no commit.
var reloaded = try ReviewState(defaults: defaults)
check(reloaded.pending == ["new-A", "new-B"], "Uncommitted queue must survive restart")
check(reloaded.reviewed == legacy, "Queue changes must not erase the old progress")
check(Set(defaults.stringArray(forKey: "reviewed") ?? []) == legacy, "Legacy storage key must remain populated")
check(defaults.string(forKey: "upAlbum") == "upper-existing-album", "Upper album must survive migration")
check(defaults.string(forKey: "downAlbum") == "lower-existing-album", "Lower album must survive migration")

reloaded.markReviewed("new-A")
check(reloaded.pending == ["new-B"], "Keeping a queued photo must remove just that photo")
check(reloaded.reviewed.contains("new-A"), "Kept photo must not be offered again")
reloaded.stageDeletion("currently-unavailable")
reloaded.completeDeletion(["new-B", "not-in-queue"])
check(reloaded.pending == ["currently-unavailable"], "Batch success must retain inaccessible / unsubmitted photos")
check(reloaded.reviewed.contains("new-B"), "Successful deletion must be recorded")
check(!reloaded.reviewed.contains("not-in-queue"), "Unrelated identifiers must not be marked reviewed")
check(reloaded.reviewed.isSuperset(of: legacy), "A batch must preserve all 2,307 original reviews")
try reloaded.save(to: defaults)
let afterDeletion = try ReviewState(defaults: defaults)
check(afterDeletion.reviewed == reloaded.reviewed && afterDeletion.pending == reloaded.pending, "Batch result must survive restart")

reloaded.resetReviewed()
check(reloaded.reviewed.isEmpty, "Explicit restart should clear completed history")
check(reloaded.pending == ["currently-unavailable"], "Explicit restart must retain pending deletion choices")
check(reloaded.shouldShow("legacy-photo-42"), "Explicit restart should offer previously completed photos")
check(!reloaded.shouldShow("currently-unavailable"), "Explicit restart must not reoffer pending photos")
print("PASS: migration of 2307 reviews, album preservation, queue persistence, keep, batch completion, and reset")
