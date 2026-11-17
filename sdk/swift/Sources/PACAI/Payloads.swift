import Foundation

// Payloads del núcleo (§4) y de los perfiles (§7). Los nombres JSON van en
// snake_case; las propiedades Swift, en camelCase. Los campos desconocidos del
// payload se guardan aparte en `Message.payloadExtras`.

public struct Hello: Codable, Equatable, Sendable, KnownFields {
    public var versions: [String]
    public var profiles: [String]?
    public var extensions: [String]?
    public var clientTools: [ClientTool]?
    public var limits: Limits?
    public var resumeAfterSeq: Int?
    public var render: JSONValue?
    public var implementation: NameVersion?
    /// Un cliente que solo mira una sesión en marcha (propuesta de observadores).
    public var observe: Bool?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case versions, profiles, extensions, limits, render, implementation, observe
        case clientTools = "client_tools", resumeAfterSeq = "resume_after_seq"
    }
    public init(versions: [String] = [PACAI.version], profiles: [String]? = [], extensions: [String]? = [],
                clientTools: [ClientTool]? = nil, limits: Limits? = nil, resumeAfterSeq: Int? = nil,
                render: JSONValue? = nil, implementation: NameVersion? = nil, observe: Bool? = nil) {
        self.versions = versions; self.profiles = profiles; self.extensions = extensions
        self.clientTools = clientTools; self.limits = limits; self.resumeAfterSeq = resumeAfterSeq
        self.render = render; self.implementation = implementation; self.observe = observe
    }
}

public struct SessionStarted: Codable, Equatable, Sendable, KnownFields {
    public var version: String
    public var profiles: [String]
    public var extensions: [String]
    public var agent: NameVersion?
    public var resumed: Bool?
    public var resumeAfterSeq: Int?
    /// La sesión de un observador (propuesta de observadores).
    public var observe: Bool?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case version, profiles, extensions, agent, resumed, observe, resumeAfterSeq = "resume_after_seq"
    }
    public init(version: String = PACAI.version, profiles: [String] = [], extensions: [String] = [],
                agent: NameVersion? = nil, resumed: Bool? = nil, resumeAfterSeq: Int? = nil, observe: Bool? = nil) {
        self.version = version; self.profiles = profiles; self.extensions = extensions
        self.agent = agent; self.resumed = resumed; self.resumeAfterSeq = resumeAfterSeq; self.observe = observe
    }
}

public struct Input: Codable, Equatable, Sendable, KnownFields {
    public enum Mode: String, Codable, Sendable { case newRun = "new_run", steer }
    public var blocks: [Block]
    public var mode: Mode?
    public var runId: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case blocks, mode, runId = "run_id" }
    public init(blocks: [Block], mode: Mode? = .newRun, runId: String? = nil) {
        self.blocks = blocks; self.mode = mode; self.runId = runId
    }
}

/// Ejecución raíz (`inputId`) o subejecución (`parentRunId`, §4.9).
public struct RunStarted: Codable, Equatable, Sendable, KnownFields {
    public var inputId: String?
    public var parentRunId: String?
    public var toolCallId: String?
    public var agent: SubagentInfo?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case inputId = "input_id", parentRunId = "parent_run_id", toolCallId = "tool_call_id", agent
    }
    public init(inputId: String? = nil, parentRunId: String? = nil, toolCallId: String? = nil,
                agent: SubagentInfo? = nil) {
        self.inputId = inputId; self.parentRunId = parentRunId; self.toolCallId = toolCallId; self.agent = agent
    }
    public var isSubrun: Bool { parentRunId != nil }
}

public struct RunFinished: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    public var outcome: Outcome
    public var detail: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case runId = "run_id", outcome, detail }
    public init(runId: String, outcome: Outcome = .success, detail: String? = nil) {
        self.runId = runId; self.outcome = outcome; self.detail = detail
    }
}

public struct MessageStart: Codable, Equatable, Sendable, KnownFields {
    public enum Role: String, Codable, Sendable { case assistant, user, system, tool }
    public var runId: String
    public var role: Role
    public var blocks: [Block]?
    enum CodingKeys: String, CodingKey, CaseIterable { case runId = "run_id", role, blocks }
    public init(runId: String, role: Role = .assistant, blocks: [Block]? = nil) {
        self.runId = runId; self.role = role; self.blocks = blocks
    }
}

public struct MessageDelta: Codable, Equatable, Sendable, KnownFields {
    public var messageId: String
    public var blocks: [Block]
    enum CodingKeys: String, CodingKey, CaseIterable { case messageId = "message_id", blocks }
    public init(messageId: String, blocks: [Block]) { self.messageId = messageId; self.blocks = blocks }
}

public struct MessageEnd: Codable, Equatable, Sendable, KnownFields {
    public var messageId: String
    public var blocks: [Block]?
    enum CodingKeys: String, CodingKey, CaseIterable { case messageId = "message_id", blocks }
    public init(messageId: String, blocks: [Block]? = nil) { self.messageId = messageId; self.blocks = blocks }
}

public struct ToolStart: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    public var name: String
    public var arguments: [String: JSONValue]
    public var side: Sender
    public var title: String?
    public var approvalId: String?
    /// Argumentos acortados por tamaño: la llamada no se puede aprobar (§4.4).
    public var truncated: Bool?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case runId = "run_id", name, arguments, side, title, approvalId = "approval_id", truncated
    }
    public init(runId: String, name: String, arguments: [String: JSONValue] = [:], side: Sender = .agent,
                title: String? = nil, approvalId: String? = nil, truncated: Bool? = nil) {
        self.runId = runId; self.name = name; self.arguments = arguments; self.side = side
        self.title = title; self.approvalId = approvalId; self.truncated = truncated
    }
}

public struct ToolEnd: Codable, Equatable, Sendable, KnownFields {
    public enum Status: String, Codable, Sendable { case success, error, cancelled }
    public var toolCallId: String
    public var status: Status
    public var output: [Block]?
    public var summary: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case toolCallId = "tool_call_id", status, output, summary }
    public init(toolCallId: String, status: Status = .success, output: [Block]? = nil, summary: String? = nil) {
        self.toolCallId = toolCallId; self.status = status; self.output = output; self.summary = summary
    }
}

public enum ApprovalScope: String, Codable, Sendable { case once, session }

public struct ApprovalRequest: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    public var toolCallId: String
    public var name: String
    public var arguments: [String: JSONValue]
    public var digest: String
    public var reason: String
    public var scopes: [ApprovalScope]
    /// Instante límite. Sin él, la petición no caduca (§4.5).
    public var expires: String?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case runId = "run_id", toolCallId = "tool_call_id", name, arguments, digest, reason, scopes, expires
    }
    public init(runId: String, toolCallId: String, name: String, arguments: [String: JSONValue], digest: String,
                reason: String, scopes: [ApprovalScope], expires: String? = nil) {
        self.runId = runId; self.toolCallId = toolCallId; self.name = name; self.arguments = arguments
        self.digest = digest; self.reason = reason; self.scopes = scopes; self.expires = expires
    }
}

public struct ApprovalResult: Codable, Equatable, Sendable, KnownFields {
    /// `approved` y `denied` los envía el cliente; `expired` y `cancelled`, el agente (§4.5). A un observador, el
    /// agente le reenvía además la decisión del dueño con `relayed` (propuesta de observadores).
    public enum Decision: String, Codable, Sendable { case approved, denied, expired, cancelled }
    public var decision: Decision
    public var scope: ApprovalScope?
    public var reason: String?
    public var relayed: Bool?
    enum CodingKeys: String, CodingKey, CaseIterable { case decision, scope, reason, relayed }
    public init(decision: Decision, scope: ApprovalScope? = nil, reason: String? = nil, relayed: Bool? = nil) {
        self.decision = decision; self.scope = scope; self.reason = reason; self.relayed = relayed
    }
}

public struct Interrupt: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    enum CodingKeys: String, CodingKey, CaseIterable { case runId = "run_id" }
    public init(runId: String) { self.runId = runId }
}

public struct Usage: Codable, Equatable, Sendable, KnownFields {
    public var runId: String?
    public var inputTokens: Int?
    public var outputTokens: Int?
    public var cachedTokens: Int?
    public var contextTokens: Int?
    public var contextLimit: Int?
    public var cost: Cost?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case runId = "run_id", inputTokens = "input_tokens", outputTokens = "output_tokens"
        case cachedTokens = "cached_tokens", contextTokens = "context_tokens", contextLimit = "context_limit", cost
    }
    public init(runId: String? = nil, inputTokens: Int? = nil, outputTokens: Int? = nil, cachedTokens: Int? = nil,
                contextTokens: Int? = nil, contextLimit: Int? = nil, cost: Cost? = nil) {
        self.runId = runId; self.inputTokens = inputTokens; self.outputTokens = outputTokens
        self.cachedTokens = cachedTokens; self.contextTokens = contextTokens; self.contextLimit = contextLimit
        self.cost = cost
    }
}

public struct Heartbeat: Codable, Equatable, Sendable, KnownFields {
    public var lastSeq: Int
    enum CodingKeys: String, CodingKey, CaseIterable { case lastSeq = "last_seq" }
    public init(lastSeq: Int) { self.lastSeq = lastSeq }
}

public struct ErrorPayload: Codable, Equatable, Sendable, KnownFields {
    public var code: String
    public var message: String
    public var ref: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case code, message, ref }
    public init(code: String, message: String, ref: String? = nil) {
        self.code = code; self.message = message; self.ref = ref
    }
}

public struct Close: Codable, Equatable, Sendable, KnownFields {
    public var reason: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case reason }
    public init(reason: String? = nil) { self.reason = reason }
}

/// Respuesta a una reanudación sin reenvío (§6). Los mensajes incrustados son mensajes PACAI completos.
public struct Snapshot: Codable, Equatable, Sendable, KnownFields {
    public var runs: [RunState]
    public var pendingApprovals: [Message]
    public var lastMessages: [Message]?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case runs, pendingApprovals = "pending_approvals", lastMessages = "last_messages"
    }
    public init(runs: [RunState], pendingApprovals: [Message] = [], lastMessages: [Message]? = nil) {
        self.runs = runs; self.pendingApprovals = pendingApprovals; self.lastMessages = lastMessages
    }
}

public struct VoiceTurn: Codable, Equatable, Sendable, KnownFields {
    public enum State: String, Codable, Sendable {
        case clientSpeaking = "client_speaking", agentListening = "agent_listening", bargeIn = "barge_in"
    }
    public var state: State
    enum CodingKeys: String, CodingKey, CaseIterable { case state }
    public init(state: State) { self.state = state }
}

public struct StateSnapshot: Codable, Equatable, Sendable, KnownFields {
    public var agent: [String: JSONValue]?
    public var client: [String: JSONValue]?
    enum CodingKeys: String, CodingKey, CaseIterable { case agent, client }
    public init(agent: [String: JSONValue]? = nil, client: [String: JSONValue]? = nil) {
        self.agent = agent; self.client = client
    }
}

public struct StateDelta: Codable, Equatable, Sendable, KnownFields {
    public var patch: [PatchOperation]
    enum CodingKeys: String, CodingKey, CaseIterable { case patch }
    public init(patch: [PatchOperation]) { self.patch = patch }
}

public struct PlanUpdated: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    public var steps: [PlanStep]
    enum CodingKeys: String, CodingKey, CaseIterable { case runId = "run_id", steps }
    public init(runId: String, steps: [PlanStep]) { self.runId = runId; self.steps = steps }
}

public struct DiffUpdated: Codable, Equatable, Sendable, KnownFields {
    public var runId: String
    public var files: [DiffFile]
    public var patch: String?
    enum CodingKeys: String, CodingKey, CaseIterable { case runId = "run_id", files, patch }
    public init(runId: String, files: [DiffFile], patch: String? = nil) {
        self.runId = runId; self.files = files; self.patch = patch
    }
}

/// Intención expresiva (§7.4). Los valores son abiertos: el cliente ignora lo que no sepa representar.
public struct Expression: Codable, Equatable, Sendable, KnownFields {
    public var runId: String?
    public var messageId: String?
    public var emotion: String?
    public var intensity: Double?
    public var gesture: String?
    public var voiceStyle: String?
    public var durationMs: Int?
    public var character: String?
    enum CodingKeys: String, CodingKey, CaseIterable {
        case runId = "run_id", messageId = "message_id", emotion, intensity, gesture
        case voiceStyle = "voice_style", durationMs = "duration_ms", character
    }
    public init(runId: String? = nil, messageId: String? = nil, emotion: String? = nil, intensity: Double? = nil,
                gesture: String? = nil, voiceStyle: String? = nil, durationMs: Int? = nil, character: String? = nil) {
        self.runId = runId; self.messageId = messageId; self.emotion = emotion; self.intensity = intensity
        self.gesture = gesture; self.voiceStyle = voiceStyle; self.durationMs = durationMs; self.character = character
    }
}
