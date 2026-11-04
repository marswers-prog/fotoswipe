import Foundation

func check(_ condition: @autoclosure () -> Bool, _ reason: String) {
    guard condition() else { fatalError(reason) }
}
func fingerprint(_ data: Data, role: Int = 1) -> ResourceFingerprint {
    var digest = StreamingResourceDigest()
    digest.update(data)
    return digest.fingerprint(role: role, uniformType: "public.jpeg")
}
let imageBytes = Data("original complete photo bytes".utf8)
let original = fingerprint(imageBytes)
var streamed = StreamingResourceDigest()
streamed.update(imageBytes.prefix(4)); streamed.update(imageBytes.dropFirst(4))
check(streamed.fingerprint(role: 1, uniformType: "public.jpeg") == original, "Resource fingerprints must be independent of delivery chunk size")
check(original != fingerprint(Data("different complete photo data".utf8)), "Different source files must not be duplicates")
let videoA = fingerprint(Data("live photo movie A".utf8), role: 9)
let videoB = fingerprint(Data("live photo movie B".utf8), role: 9)
let editA = fingerprint(Data("crop A".utf8), role: 7)
let editB = fingerprint(Data("crop B".utf8), role: 7)
func signature(_ resources: [ResourceFingerprint], width: Int = 100) -> ExactDuplicateSignature {
    ExactDuplicateSignature(width: width, height: 100, subtype: 0, resources: resources)
}
check(signature([original, videoA]) == signature([videoA, original]), "PhotoKit resource enumeration order must not matter")
check(signature([original, videoA]) != signature([original, videoB]), "Matching still images with different Live Photo movies must stay separate")
check(signature([original, editA]) != signature([original, editB]), "Matching originals with different edit data must stay separate")
check(signature([original]) != signature([original, editA]), "Original and edited versions must stay separate")
check(signature([original]) != signature([original], width: 200), "Different dimensions must stay separate")

let temporary = FileManager.default.temporaryDirectory.appendingPathComponent("FotoSwipe-duplicate-tests-\(UUID().uuidString)")
try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: temporary) }
let first = temporary.appendingPathComponent("first"), second = temporary.appendingPathComponent("second")
try imageBytes.write(to: first); try imageBytes.write(to: second)
check(ExactFileComparison.equal(first, second), "Identical files must pass final byte comparison")
try Data(repeating: 65, count: imageBytes.count).write(to: second)
check(!ExactFileComparison.equal(first, second), "Even same-sized hash candidates must fail if their bytes differ")
check(!ExactFileComparison.equal(first, temporary.appendingPathComponent("missing")), "Missing files cannot pass verification")

let choice = DuplicateChoice(members: ["A", "B", "C"], keeper: "B", selected: true)
let ignored = DuplicateChoice(members: ["D", "E"], keeper: "D", selected: false)
let plan = try DuplicateDeletionPlan(choices: [choice, ignored])
check(plan.deleteIDs == ["A", "C"] && plan.keepIDs == ["B"], "Only selected extra copies may be deleted; chosen keeper must survive")
let emptyPlan = try DuplicateDeletionPlan(choices: [])
check(emptyPlan.deleteIDs.isEmpty, "No selection must not delete anything")
func rejected(_ choices: [DuplicateChoice]) -> Bool {
    do { _ = try DuplicateDeletionPlan(choices: choices); return false } catch { return true }
}
check(rejected([DuplicateChoice(members: ["A", "B"], keeper: "missing", selected: true)]), "A missing keeper must reject deletion")
check(rejected([DuplicateChoice(members: ["A"], keeper: "A", selected: true)]), "Singletons must never be deleted")
check(rejected([DuplicateChoice(members: ["A", "A"], keeper: "A", selected: true)]), "Repeated identifiers must reject deletion")
check(rejected([choice, DuplicateChoice(members: ["B", "D"], keeper: "D", selected: true)]), "Conflicting groups must not delete another group's keeper")

let suite = "FotoSwipeDuplicateMigration-\(UUID().uuidString)"
let defaults = UserDefaults(suiteName: suite)!
defer { defaults.removePersistentDomain(forName: suite) }
let oldIDs = Set((0..<2307).map { "reviewed-\($0)" })
// A literal version-1.1 snapshot format, including the existing manual queue.
let oldSnapshot: [String: Any] = ["reviewed": Array(oldIDs), "pending": ["A", "B", "unrelated"]]
defaults.set(try JSONSerialization.data(withJSONObject: oldSnapshot), forKey: "reviewStateV2")
defaults.set(Array(oldIDs), forKey: "reviewed")
defaults.set("upper-album", forKey: "upAlbum"); defaults.set("lower-album", forKey: "downAlbum")
var state = try ReviewState(defaults: defaults)
check(state.reviewed == oldIDs && state.pending == ["A", "B", "unrelated"], "Version 1.1 history and manual queue must migrate unchanged")
state.recordDuplicateDeletion(deleted: plan.deleteIDs, kept: plan.keepIDs)
try state.save(to: defaults)
let restored = try ReviewState(defaults: defaults)
check(restored.reviewed.isSuperset(of: oldIDs), "All 2307 old decisions must survive duplicate cleanup")
check(restored.reviewed.isSuperset(of: ["A", "B", "C"]), "Deleted copies and explicit keeper must count as handled")
check(restored.pending == ["unrelated"], "Duplicate cleanup must preserve unrelated queue entries and remove the keeper from that queue")
check(defaults.string(forKey: "upAlbum") == "upper-album" && defaults.string(forKey: "downAlbum") == "lower-album", "Both album preferences must survive")
print("PASS: complete-file hashes, byte verification, edited/Live Photo distinctions, survivor selection, invalid plans, and version-1.1 migration of 2307 reviews plus pending queue")
