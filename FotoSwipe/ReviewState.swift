import Foundation

/// Stores the original review history and a separate, ordered deletion queue.
struct ReviewState: Codable {
    static let snapshotKey = "reviewStateV2"
    private(set) var reviewed: Set<String>
    private(set) var pending: [String]

    init(reviewed: Set<String> = [], pending: [String] = []) {
        self.reviewed = reviewed
        var seen = Set<String>()
        self.pending = pending.filter { !reviewed.contains($0) && seen.insert($0).inserted }
    }

    init(defaults: UserDefaults) throws {
        if let data = defaults.data(forKey: Self.snapshotKey) {
            let saved = try JSONDecoder().decode(Self.self, from: data)
            self.init(reviewed: saved.reviewed, pending: saved.pending)
        } else {
            // Version 1.0 stored these identifiers under this exact key.
            self.init(reviewed: Set(defaults.stringArray(forKey: "reviewed") ?? []))
        }
    }

    func save(to defaults: UserDefaults) throws {
        let data = try JSONEncoder().encode(self)
        // A single snapshot keeps history and queue consistent across launches.
        defaults.set(data, forKey: Self.snapshotKey)
        // Keep the existing history key populated; never reset it on migration.
        defaults.set(Array(reviewed), forKey: "reviewed")
    }

    func shouldShow(_ id: String) -> Bool {
        !reviewed.contains(id) && !pending.contains(id)
    }

    mutating func markReviewed(_ id: String) {
        reviewed.insert(id)
        pending.removeAll { $0 == id }
    }

    mutating func stageDeletion(_ id: String) {
        guard !reviewed.contains(id), !pending.contains(id) else { return }
        pending.append(id)
    }

    mutating func completeDeletion(_ ids: Set<String>) {
        let completed = Set(pending).intersection(ids)
        reviewed.formUnion(completed)
        pending.removeAll { completed.contains($0) }
    }

    mutating func resetReviewed() {
        reviewed.removeAll()
        // A reset must never silently empty a pending deletion queue.
    }
}
