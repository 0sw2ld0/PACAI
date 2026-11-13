import Foundation

/// Transporte `pacai+stdio` (§5.1): un mensaje JSON compacto por línea.
public enum JSONL {
    /// Límite por defecto de un mensaje (§4.1): 1 MiB.
    public static let defaultMaxBytes = 1024 * 1024

    public enum Failure: Error, Equatable {
        case messageTooLarge(Int)
    }

    /// Codifica un mensaje como una línea JSON terminada en `\n`.
    public static func encode(_ message: Message) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.withoutEscapingSlashes]
        var data = try encoder.encode(message)
        data.append(0x0A)
        return data
    }

    /// Decodifica una línea (con o sin `\n` final).
    public static func decode(_ line: Data) throws -> Message {
        try JSONDecoder().decode(Message.self, from: line)
    }

    public static func decode(_ line: String) throws -> Message {
        try decode(Data(line.utf8))
    }

    /// Decodifica todas las líneas no vacías de un texto JSONL.
    public static func decodeAll(_ data: Data) throws -> [Message] {
        try data.split(separator: 0x0A, omittingEmptySubsequences: true)
            .filter { !$0.allSatisfy { $0 == 0x20 || $0 == 0x09 || $0 == 0x0D } }
            .map { try decode(Data($0)) }
    }

    public static func encodeAll(_ messages: [Message]) throws -> Data {
        try messages.reduce(into: Data()) { $0.append(try encode($1)) }
    }
}

/// Lee mensajes de un `FileHandle` (stdin por defecto), línea a línea.
public final class JSONLReader {
    private let handle: FileHandle
    private var buffer = Data()
    private var finished = false
    public let maxBytes: Int

    public init(handle: FileHandle = .standardInput, maxBytes: Int = JSONL.defaultMaxBytes) {
        self.handle = handle
        self.maxBytes = maxBytes
    }

    /// El siguiente mensaje, o `nil` en EOF (que equivale a `close`).
    public func next() throws -> Message? {
        while true {
            if let nl = buffer.firstIndex(of: 0x0A) {
                let line = buffer[buffer.startIndex..<nl]
                buffer.removeSubrange(buffer.startIndex...nl)
                if line.count > maxBytes { throw JSONL.Failure.messageTooLarge(line.count) }
                if line.allSatisfy({ $0 == 0x20 || $0 == 0x09 || $0 == 0x0D }) { continue }
                return try JSONL.decode(Data(line))
            }
            if buffer.count > maxBytes { throw JSONL.Failure.messageTooLarge(buffer.count) }
            if finished {
                guard !buffer.isEmpty else { return nil }
                let line = buffer
                buffer.removeAll()
                if line.allSatisfy({ $0 == 0x20 || $0 == 0x09 || $0 == 0x0D }) { return nil }
                return try JSONL.decode(line)
            }
            let chunk = handle.availableData
            if chunk.isEmpty { finished = true } else { buffer.append(chunk) }
        }
    }

    /// Lee hasta EOF.
    public func readAll() throws -> [Message] {
        var out: [Message] = []
        while let m = try next() { out.append(m) }
        return out
    }
}

/// Escribe mensajes en un `FileHandle` (stdout por defecto). Es seguro entre hilos.
public final class JSONLWriter: @unchecked Sendable {
    private let handle: FileHandle
    private let lock = NSLock()
    public let maxBytes: Int

    public init(handle: FileHandle = .standardOutput, maxBytes: Int = JSONL.defaultMaxBytes) {
        self.handle = handle
        self.maxBytes = maxBytes
    }

    public func write(_ message: Message) throws {
        let data = try JSONL.encode(message)
        if data.count > maxBytes { throw JSONL.Failure.messageTooLarge(data.count) }
        lock.lock()
        defer { lock.unlock() }
        try handle.write(contentsOf: data)
    }
}

extension FileHandle {
    /// Mensajes PACAI en orden de llegada, de forma asíncrona.
    public var pacaiMessages: AsyncThrowingMapSequence<AsyncLineSequence<FileHandle.AsyncBytes>, Message> {
        bytes.lines.map { try JSONL.decode($0) }
    }
}
