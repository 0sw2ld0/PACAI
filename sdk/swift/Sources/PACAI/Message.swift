import Foundation

public enum PACAI {
    /// Versión del protocolo que implementa este paquete.
    public static let version = "0.2"
}

/// Cuerpo tipado de un mensaje: un caso por tipo del núcleo y de los perfiles.
/// Las extensiones (`espacio.nombre`) y los tipos futuros se conservan como JSON crudo.
public enum Body: Equatable, Sendable {
    case hello(Hello)
    case sessionStarted(SessionStarted)
    case input(Input)
    case runStarted(RunStarted)
    case runFinished(RunFinished)
    case messageStart(MessageStart)
    case messageDelta(MessageDelta)
    case messageEnd(MessageEnd)
    case toolStart(ToolStart)
    case toolEnd(ToolEnd)
    case approvalRequest(ApprovalRequest)
    case approvalResult(ApprovalResult)
    case interrupt(Interrupt)
    case usage(Usage)
    case heartbeat(Heartbeat)
    case error(ErrorPayload)
    case close(Close)
    case snapshot(Snapshot)
    case voiceTurn(VoiceTurn)
    case stateSnapshot(StateSnapshot)
    case stateDelta(StateDelta)
    case planUpdated(PlanUpdated)
    case diffUpdated(DiffUpdated)
    case expression(Expression)
    /// Extensión con espacio de nombres (§8), p. ej. `alfalfa.budget`.
    case `extension`(type: String, payload: [String: JSONValue])
    /// Tipo sin punto que esta versión no conoce.
    case unknown(type: String, payload: [String: JSONValue])

    /// El valor del campo `type` del sobre.
    public var type: String {
        switch self {
        case .hello: "hello"
        case .sessionStarted: "session_started"
        case .input: "input"
        case .runStarted: "run_started"
        case .runFinished: "run_finished"
        case .messageStart: "message_start"
        case .messageDelta: "message_delta"
        case .messageEnd: "message_end"
        case .toolStart: "tool_start"
        case .toolEnd: "tool_end"
        case .approvalRequest: "approval_request"
        case .approvalResult: "approval_result"
        case .interrupt: "interrupt"
        case .usage: "usage"
        case .heartbeat: "heartbeat"
        case .error: "error"
        case .close: "close"
        case .snapshot: "snapshot"
        case .voiceTurn: "voice_turn"
        case .stateSnapshot: "state_snapshot"
        case .stateDelta: "state_delta"
        case .planUpdated: "plan_updated"
        case .diffUpdated: "diff_updated"
        case .expression: "expression"
        case .extension(let t, _), .unknown(let t, _): t
        }
    }

    /// Tipos del núcleo y de los perfiles que conoce esta versión.
    public static let knownTypes: Set<String> = [
        "hello", "session_started", "input", "run_started", "run_finished", "message_start", "message_delta",
        "message_end", "tool_start", "tool_end", "approval_request", "approval_result", "interrupt", "usage",
        "heartbeat", "error", "close", "snapshot", "voice_turn", "state_snapshot", "state_delta", "plan_updated",
        "diff_updated", "expression",
    ]
}

/// Un mensaje PACAI: el sobre común (§2) y su cuerpo.
public struct Message: Codable, Equatable, Sendable {
    public var pacai: String
    public var id: String
    public var session: String
    public var sender: Sender
    public var seq: Int
    public var time: String
    public var replyTo: String?
    public var body: Body
    /// Campos del payload que el tipo no conoce. Se reenvían tal cual.
    public var payloadExtras: [String: JSONValue]
    /// Campos del sobre que esta versión no conoce. Se reenvían tal cual.
    public var envelopeExtras: [String: JSONValue]

    public var type: String { body.type }

    public init(id: String, session: String, sender: Sender, seq: Int, time: String, replyTo: String? = nil,
                body: Body, pacai: String = PACAI.version, payloadExtras: [String: JSONValue] = [:],
                envelopeExtras: [String: JSONValue] = [:]) {
        self.pacai = pacai; self.id = id; self.session = session; self.sender = sender; self.seq = seq
        self.time = time; self.replyTo = replyTo; self.body = body
        self.payloadExtras = payloadExtras; self.envelopeExtras = envelopeExtras
    }

    private static let envelopeKeys: Set<String> = ["pacai", "id", "type", "session", "sender", "seq", "time",
                                                    "reply_to", "payload"]

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: AnyKey.self)
        pacai = try c.decode(String.self, forKey: AnyKey("pacai"))
        id = try c.decode(String.self, forKey: AnyKey("id"))
        session = try c.decode(String.self, forKey: AnyKey("session"))
        sender = try c.decode(Sender.self, forKey: AnyKey("sender"))
        seq = try c.decode(Int.self, forKey: AnyKey("seq"))
        time = try c.decode(String.self, forKey: AnyKey("time"))
        replyTo = try c.decodeIfPresent(String.self, forKey: AnyKey("reply_to"))
        let type = try c.decode(String.self, forKey: AnyKey("type"))
        let payloadKey = AnyKey("payload")
        let raw = try c.decode([String: JSONValue].self, forKey: payloadKey)

        var extras: [String: JSONValue] = [:]
        func typed<P: Decodable & KnownFields>(_: P.Type) throws -> P {
            extras = raw.filter { !P.knownFieldNames.contains($0.key) }
            return try c.decode(P.self, forKey: payloadKey)
        }
        switch type {
        case "hello": body = .hello(try typed(Hello.self))
        case "session_started": body = .sessionStarted(try typed(SessionStarted.self))
        case "input": body = .input(try typed(Input.self))
        case "run_started": body = .runStarted(try typed(RunStarted.self))
        case "run_finished": body = .runFinished(try typed(RunFinished.self))
        case "message_start": body = .messageStart(try typed(MessageStart.self))
        case "message_delta": body = .messageDelta(try typed(MessageDelta.self))
        case "message_end": body = .messageEnd(try typed(MessageEnd.self))
        case "tool_start": body = .toolStart(try typed(ToolStart.self))
        case "tool_end": body = .toolEnd(try typed(ToolEnd.self))
        case "approval_request": body = .approvalRequest(try typed(ApprovalRequest.self))
        case "approval_result": body = .approvalResult(try typed(ApprovalResult.self))
        case "interrupt": body = .interrupt(try typed(Interrupt.self))
        case "usage": body = .usage(try typed(Usage.self))
        case "heartbeat": body = .heartbeat(try typed(Heartbeat.self))
        case "error": body = .error(try typed(ErrorPayload.self))
        case "close": body = .close(try typed(Close.self))
        case "snapshot": body = .snapshot(try typed(Snapshot.self))
        case "voice_turn": body = .voiceTurn(try typed(VoiceTurn.self))
        case "state_snapshot": body = .stateSnapshot(try typed(StateSnapshot.self))
        case "state_delta": body = .stateDelta(try typed(StateDelta.self))
        case "plan_updated": body = .planUpdated(try typed(PlanUpdated.self))
        case "diff_updated": body = .diffUpdated(try typed(DiffUpdated.self))
        case "expression": body = .expression(try typed(Expression.self))
        default:
            body = type.contains(".") ? .extension(type: type, payload: raw) : .unknown(type: type, payload: raw)
        }
        payloadExtras = extras

        var sobre: [String: JSONValue] = [:]
        for key in c.allKeys where !Self.envelopeKeys.contains(key.stringValue) {
            sobre[key.stringValue] = try c.decode(JSONValue.self, forKey: key)
        }
        envelopeExtras = sobre
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: AnyKey.self)
        try c.encode(pacai, forKey: AnyKey("pacai"))
        try c.encode(id, forKey: AnyKey("id"))
        try c.encode(type, forKey: AnyKey("type"))
        try c.encode(session, forKey: AnyKey("session"))
        try c.encode(sender, forKey: AnyKey("sender"))
        try c.encode(seq, forKey: AnyKey("seq"))
        try c.encode(time, forKey: AnyKey("time"))
        try c.encodeIfPresent(replyTo, forKey: AnyKey("reply_to"))
        try c.encode(JSONValue.object(try payloadObject()), forKey: AnyKey("payload"))
        for (k, v) in envelopeExtras where !Self.envelopeKeys.contains(k) {
            try c.encode(v, forKey: AnyKey(k))
        }
    }

    /// El payload como objeto JSON, con los campos desconocidos incluidos.
    public func payloadObject() throws -> [String: JSONValue] {
        var obj: [String: JSONValue]
        switch body {
        case .hello(let p): obj = try Self.object(p)
        case .sessionStarted(let p): obj = try Self.object(p)
        case .input(let p): obj = try Self.object(p)
        case .runStarted(let p): obj = try Self.object(p)
        case .runFinished(let p): obj = try Self.object(p)
        case .messageStart(let p): obj = try Self.object(p)
        case .messageDelta(let p): obj = try Self.object(p)
        case .messageEnd(let p): obj = try Self.object(p)
        case .toolStart(let p): obj = try Self.object(p)
        case .toolEnd(let p): obj = try Self.object(p)
        case .approvalRequest(let p): obj = try Self.object(p)
        case .approvalResult(let p): obj = try Self.object(p)
        case .interrupt(let p): obj = try Self.object(p)
        case .usage(let p): obj = try Self.object(p)
        case .heartbeat(let p): obj = try Self.object(p)
        case .error(let p): obj = try Self.object(p)
        case .close(let p): obj = try Self.object(p)
        case .snapshot(let p): obj = try Self.object(p)
        case .voiceTurn(let p): obj = try Self.object(p)
        case .stateSnapshot(let p): obj = try Self.object(p)
        case .stateDelta(let p): obj = try Self.object(p)
        case .planUpdated(let p): obj = try Self.object(p)
        case .diffUpdated(let p): obj = try Self.object(p)
        case .expression(let p): obj = try Self.object(p)
        case .extension(_, let p), .unknown(_, let p): return p
        }
        for (k, v) in payloadExtras where obj[k] == nil {
            obj[k] = v
        }
        return obj
    }

    private static func object<P: Encodable>(_ p: P) throws -> [String: JSONValue] {
        let data = try JSONEncoder().encode(p)
        return try JSONDecoder().decode([String: JSONValue].self, from: data)
    }
}
