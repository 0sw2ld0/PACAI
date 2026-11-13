import Foundation
import XCTest
@testable import PACAI

/// Decodifica y vuelve a codificar todos los ejemplos válidos de `conformance/valid`.
final class ConformanceTests: XCTestCase {
    static let conformance = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent()
        .appendingPathComponent("conformance")

    static func validFiles() throws -> [URL] {
        let dir = conformance.appendingPathComponent("valid")
        return try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "jsonl" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    static func lines(_ url: URL) throws -> [Data] {
        try Data(contentsOf: url).split(separator: 0x0A).map { Data($0) }
    }

    /// Compara dos documentos JSON por su valor, sin depender del orden de las claves.
    func assertSameJSON(_ a: Data, _ b: Data, _ context: String, file: StaticString = #filePath, line: UInt = #line) throws {
        let x = try JSONSerialization.jsonObject(with: a) as? NSDictionary
        let y = try JSONSerialization.jsonObject(with: b) as? NSDictionary
        XCTAssertNotNil(x, context, file: file, line: line)
        XCTAssertEqual(x, y, context, file: file, line: line)
    }

    func testHayEjemplosValidos() throws {
        XCTAssertGreaterThanOrEqual(try Self.validFiles().count, 11)
    }

    func testIdaYVueltaDeTodosLosEjemplosValidos() throws {
        var total = 0
        for url in try Self.validFiles() {
            for (n, line) in try Self.lines(url).enumerated() {
                let context = "\(url.lastPathComponent):\(n + 1)"
                let message = try JSONDecoder().decode(Message.self, from: line)
                // Ningún tipo del núcleo cae en .unknown, y lo desconocido solo aparece en extensiones.
                if case .unknown(let t, _) = message.body { XCTFail("\(context): tipo \(t) sin tipar") }
                XCTAssertTrue(message.payloadExtras.isEmpty, "\(context): extras \(message.payloadExtras)")
                let encoded = try JSONL.encode(message)
                XCTAssertEqual(encoded.last, 0x0A)
                XCTAssertEqual(encoded.filter { $0 == 0x0A }.count, 1, context)
                try assertSameJSON(line, encoded, context)
                // Una segunda vuelta da exactamente el mismo valor.
                XCTAssertEqual(try JSONL.decode(encoded), message, context)
                total += 1
            }
        }
        XCTAssertGreaterThan(total, 100)
    }

    func testDecodeAllYEncodeAll() throws {
        for url in try Self.validFiles() {
            let data = try Data(contentsOf: url)
            let messages = try JSONL.decodeAll(data)
            XCTAssertEqual(try JSONL.decodeAll(try JSONL.encodeAll(messages)), messages, url.lastPathComponent)
        }
    }

    func testTiposConcretos() throws {
        let sub = try Self.validFiles().first { $0.lastPathComponent.hasPrefix("06-") }!
        let messages = try JSONL.decodeAll(Data(contentsOf: sub))
        let subruns = messages.compactMap { m -> RunStarted? in
            if case .runStarted(let r) = m.body, r.isSubrun { return r }
            return nil
        }
        XCTAssertEqual(subruns.count, 2)
        XCTAssertEqual(subruns.first?.agent?.name, "revisor")
        XCTAssertNotNil(subruns.first?.toolCallId)
        let reutilizada = messages.contains { m in
            if case .toolStart(let t) = m.body { return t.approvalId != nil }
            return false
        }
        XCTAssertTrue(reutilizada)

        let snap = try Self.validFiles().first { $0.lastPathComponent.hasPrefix("08-") }!
        let snapshot = try JSONL.decodeAll(Data(contentsOf: snap)).compactMap { m -> Snapshot? in
            if case .snapshot(let s) = m.body { return s }
            return nil
        }.first
        XCTAssertEqual(snapshot?.runs.first?.status, .active)
        XCTAssertEqual(snapshot?.pendingApprovals.first?.type, "approval_request")
        XCTAssertEqual(snapshot?.lastMessages?.count, 2)
    }
}
