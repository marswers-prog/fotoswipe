import Foundation
import CryptoKit

struct ResourceFingerprint: Hashable {
    let role: Int
    let uniformType: String
    let byteCount: Int64
    let sha256: String
}

struct StreamingResourceDigest {
    private var hash = SHA256()
    private var count: Int64 = 0

    mutating func update(_ data: Data) {
        hash.update(data: data)
        count += Int64(data.count)
    }

    func fingerprint(role: Int, uniformType: String) -> ResourceFingerprint {
        let digest = hash.finalize().map { String(format: "%02x", $0) }.joined()
        return ResourceFingerprint(role: role, uniformType: uniformType, byteCount: count, sha256: digest)
    }
}

struct ExactDuplicateSignature: Hashable {
    let width: Int
    let height: Int
    let subtype: UInt
    let resources: [ResourceFingerprint]

    init(width: Int, height: Int, subtype: UInt, resources: [ResourceFingerprint]) {
        self.width = width; self.height = height; self.subtype = subtype
        self.resources = resources.sorted {
            ($0.role, $0.uniformType, $0.byteCount, $0.sha256) < ($1.role, $1.uniformType, $1.byteCount, $1.sha256)
        }
    }
}

enum DuplicateIssue: LocalizedError {
    case changed, invalidSelection, unreadable
    var errorDescription: String? {
        switch self {
        case .changed: return "Die Fotos oder die Zugriffsrechte haben sich geändert. Bitte erneut nach Duplikaten suchen."
        case .invalidSelection: return "Die Auswahl ist nicht mehr gültig. Pro Gruppe muss mindestens ein Foto erhalten bleiben."
        case .unreadable: return "Mindestens eine Fotodatei konnte nicht vollständig gelesen werden. Es wird nichts gelöscht."
        }
    }
}

struct DuplicateChoice {
    let members: [String]
    let keeper: String
    let selected: Bool
}

struct DuplicateDeletionPlan {
    let deleteIDs: Set<String>
    let keepIDs: Set<String>

    init(choices: [DuplicateChoice]) throws {
        var deleted = Set<String>(), kept = Set<String>(), all = Set<String>()
        for choice in choices where choice.selected {
            let members = Set(choice.members)
            guard members.count > 1, members.count == choice.members.count,
                  members.contains(choice.keeper), all.isDisjoint(with: members) else {
                throw DuplicateIssue.invalidSelection
            }
            all.formUnion(members)
            kept.insert(choice.keeper)
            deleted.formUnion(members.subtracting([choice.keeper]))
        }
        guard deleted.isDisjoint(with: kept) else { throw DuplicateIssue.invalidSelection }
        deleteIDs = deleted; keepIDs = kept
    }
}

enum ExactFileComparison {
    // Hashes find candidates. This final byte comparison decides equality.
    static func equal(_ first: URL, _ second: URL) -> Bool {
        FileManager.default.contentsEqual(atPath: first.path, andPath: second.path)
    }
}
