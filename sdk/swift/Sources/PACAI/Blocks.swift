import Foundation

/// Tipos que pueden dar la lista de sus campos conocidos, para separar los desconocidos.
protocol KnownFields {
    associatedtype CodingKeys: CodingKey & CaseIterable
}

extension KnownFields {
    static var knownFieldNames: Set<String> { Set(CodingKeys.allCases.map(\.stringValue)) }
}

/// Bloque de contenido (§3). Un bloque de tipo desconocido se conserva en `.other`.
public enum Block: Codable, Equatable, Sendable {
    case text(String)
    case file(name: String, mediaType: String, data: String? = nil, url: String? = nil)
    case structured(schema: String, data: [String: JSONValue])
    case audio(mediaType: String, encoding: String, data: String? = nil, url: String? = nil, transcript: String? = nil)
    case other(JSONValue)

    private enum K: String, CodingKey {
        case type, text, name, data, url, schema, encoding, transcript
        case mediaType = "media_type"
    }

    public init(from decoder: Decoder) throws {
        let raw = try JSONValue(from: decoder)
        let c = try decoder.container(keyedBy: K.self)
        // Si sobran campos, se conserva entero para no perder nada.
        let conocidos: [String: Set<String>] = [
            "text": ["type", "text"], "file": ["type", "name", "media_type", "data", "url"],
            "structured": ["type", "schema", "data"],
            "audio": ["type", "media_type", "encoding", "data", "url", "transcript"],
        ]
        let tipo = try? c.decode(String.self, forKey: .type)
        guard let tipo, let campos = conocidos[tipo], let obj = raw.objectValue,
              Set(obj.keys).isSubset(of: campos) else {
            self = .other(raw)
            return
        }
        do {
            switch tipo {
            case "text":
                self = .text(try c.decode(String.self, forKey: .text))
            case "file":
                self = .file(name: try c.decode(String.self, forKey: .name),
                             mediaType: try c.decode(String.self, forKey: .mediaType),
                             data: try c.decodeIfPresent(String.self, forKey: .data),
                             url: try c.decodeIfPresent(String.self, forKey: .url))
            case "structured":
                self = .structured(schema: try c.decode(String.self, forKey: .schema),
                                   data: try c.decode([String: JSONValue].self, forKey: .data))
            default:
                self = .audio(mediaType: try c.decode(String.self, forKey: .mediaType),
                              encoding: try c.decode(String.self, forKey: .encoding),
                              data: try c.decodeIfPresent(String.self, forKey: .data),
                              url: try c.decodeIfPresent(String.self, forKey: .url),
                              transcript: try c.decodeIfPresent(String.self, forKey: .transcript))
            }
        } catch {
            self = .other(raw)
        }
    }

    public func encode(to encoder: Encoder) throws {
        if case .other(let raw) = self {
            try raw.encode(to: encoder)
            return
        }
        var c = encoder.container(keyedBy: K.self)
        switch self {
        case .text(let t):
            try c.encode("text", forKey: .type)
            try c.encode(t, forKey: .text)
        case let .file(name, mediaType, data, url):
            try c.encode("file", forKey: .type)
            try c.encode(name, forKey: .name)
            try c.encode(mediaType, forKey: .mediaType)
            try c.encodeIfPresent(data, forKey: .data)
            try c.encodeIfPresent(url, forKey: .url)
        case let .structured(schema, data):
            try c.encode("structured", forKey: .type)
            try c.encode(schema, forKey: .schema)
            try c.encode(data, forKey: .data)
        case let .audio(mediaType, encoding, data, url, transcript):
            try c.encode("audio", forKey: .type)
            try c.encode(mediaType, forKey: .mediaType)
            try c.encode(encoding, forKey: .encoding)
            try c.encodeIfPresent(data, forKey: .data)
            try c.encodeIfPresent(url, forKey: .url)
            try c.encodeIfPresent(transcript, forKey: .transcript)
        case .other:
            break
        }
    }

    /// El texto del bloque, si es de texto.
    public var text: String? {
        if case .text(let t) = self { return t }
        return nil
    }
}

public enum Sender: String, Codable, Sendable {
    case agent, client
}

public struct NameVersion: Codable, Equatable, Sendable {
    public var name: String?
    public var version: String?
    public init(name: String? = nil, version: String? = nil) { self.name = name; self.version = version }
}

public struct ClientTool: Codable, Equatable, Sendable {
    public var name: String
    public var description: String?
    public var inputSchema: [String: JSONValue]
    enum CodingKeys: String, CodingKey { case name, description, inputSchema = "input_schema" }
    public init(name: String, description: String? = nil, inputSchema: [String: JSONValue] = ["type": "object"]) {
        self.name = name; self.description = description; self.inputSchema = inputSchema
    }
}

public struct Limits: Codable, Equatable, Sendable {
    public var maxMessageBytes: Int?
    enum CodingKeys: String, CodingKey { case maxMessageBytes = "max_message_bytes" }
    public init(maxMessageBytes: Int? = nil) { self.maxMessageBytes = maxMessageBytes }
}

/// `agent` de una subejecución (§4.9).
public struct SubagentInfo: Codable, Equatable, Sendable {
    public var name: String
    public var description: String?
    public init(name: String, description: String? = nil) { self.name = name; self.description = description }
}

public enum Outcome: String, Codable, Sendable {
    case success, interrupted, failed, blocked
}

/// Estado de una ejecución dentro de `snapshot` (§6).
public struct RunState: Codable, Equatable, Sendable {
    public enum Status: String, Codable, Sendable { case active, finished }
    public var runId: String
    public var status: Status
    public var outcome: Outcome?
    public var parentRunId: String?
    enum CodingKeys: String, CodingKey {
        case runId = "run_id", status, outcome, parentRunId = "parent_run_id"
    }
    public init(runId: String, status: Status, outcome: Outcome? = nil, parentRunId: String? = nil) {
        self.runId = runId; self.status = status; self.outcome = outcome; self.parentRunId = parentRunId
    }
}

public struct Cost: Codable, Equatable, Sendable {
    public var amount: Double
    public var currency: String
    public init(amount: Double, currency: String) { self.amount = amount; self.currency = currency }
}

public struct PlanStep: Codable, Equatable, Sendable {
    public enum Status: String, Codable, Sendable { case pending, inProgress = "in_progress", completed }
    public var text: String
    public var status: Status
    public init(text: String, status: Status) { self.text = text; self.status = status }
}

public struct DiffFile: Codable, Equatable, Sendable {
    public var path: String
    public var added: Int?
    public var removed: Int?
    public init(path: String, added: Int? = nil, removed: Int? = nil) {
        self.path = path; self.added = added; self.removed = removed
    }
}

/// Operación JSON Patch (RFC 6902). `value` y `from` se guardan tal cual.
public struct PatchOperation: Codable, Equatable, Sendable {
    public var op: String
    public var path: String
    public var from: String?
    public var value: JSONValue?
    public init(op: String, path: String, from: String? = nil, value: JSONValue? = nil) {
        self.op = op; self.path = path; self.from = from; self.value = value
    }
    enum CodingKeys: String, CodingKey { case op, path, from, value }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        op = try c.decode(String.self, forKey: .op)
        path = try c.decode(String.self, forKey: .path)
        from = try c.decodeIfPresent(String.self, forKey: .from)
        // "value": null es un valor legítimo y distinto de no tener value.
        value = c.contains(.value) ? try c.decode(JSONValue.self, forKey: .value) : nil
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(op, forKey: .op)
        try c.encode(path, forKey: .path)
        try c.encodeIfPresent(from, forKey: .from)
        if let value { try c.encode(value, forKey: .value) }
    }
}
