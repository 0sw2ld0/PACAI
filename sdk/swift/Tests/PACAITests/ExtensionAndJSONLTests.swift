import Foundation
import XCTest
@testable import PACAI

final class ExtensionAndJSONLTests: XCTestCase {
    let session = "s_prueba_0123456789abcdef"

    func object(_ data: Data) throws -> NSDictionary {
        try JSONSerialization.jsonObject(with: data) as! NSDictionary
    }

    func testExtensionDesconocidaSeConservaCruda() throws {
        let line = """
        {"pacai":"0.3","id":"m_00000001","type":"cuyworld.scene","session":"\(session)","sender":"agent","seq":1,\
        "time":"2026-11-12T10:00:00Z","payload":{"scene":"bosque","npcs":[{"name":"Tito","hp":3.5}],"night":true,"x":null}}
        """
        let m = try JSONL.decode(line)
        guard case .extension(let type, let payload) = m.body else { return XCTFail("no es extensión") }
        XCTAssertEqual(type, "cuyworld.scene")
        XCTAssertEqual(payload["night"], .bool(true))
        XCTAssertEqual(payload["x"], .null)
        XCTAssertEqual(try object(JSONL.encode(m)), try object(Data(line.utf8)))
    }

    func testTipoFuturoYCamposDesconocidos() throws {
        let line = """
        {"pacai":"0.3","id":"m_00000002","type":"close","session":"\(session)","sender":"client","seq":2,\
        "time":"2026-11-12T10:00:00Z","trace":"abc","payload":{"reason":"fin","futuro":{"a":[1,2]}}}
        """
        let m = try JSONL.decode(line)
        XCTAssertEqual(m.envelopeExtras["trace"], "abc")
        XCTAssertEqual(m.payloadExtras["futuro"], ["a": [1, 2]])
        XCTAssertEqual(try object(JSONL.encode(m)), try object(Data(line.utf8)))

        let futuro = line.replacingOccurrences(of: "\"close\"", with: "\"teleport\"")
        guard case .unknown(let t, _) = try JSONL.decode(futuro).body else { return XCTFail("debía ser .unknown") }
        XCTAssertEqual(t, "teleport")
    }

    func testBloqueDesconocidoSeConserva() throws {
        let line = """
        {"pacai":"0.3","id":"m_00000003","type":"message_delta","session":"\(session)","sender":"agent","seq":3,\
        "time":"2026-11-12T10:00:00Z","payload":{"message_id":"m_00000002","blocks":[{"type":"text","text":"hola"},\
        {"type":"a2ui","tree":{"k":1}},{"type":"text","text":"x","lang":"es"}]}}
        """
        let m = try JSONL.decode(line)
        guard case .messageDelta(let d) = m.body else { return XCTFail() }
        XCTAssertEqual(d.blocks.first?.text, "hola")
        if case .other = d.blocks[1] {} else { XCTFail("el bloque a2ui debía quedar crudo") }
        if case .other = d.blocks[2] {} else { XCTFail("un texto con campos extra debía quedar crudo") }
        XCTAssertEqual(try object(JSONL.encode(m)), try object(Data(line.utf8)))
    }

    func testConstruirYEscribirConElWriter() throws {
        let pipe = Pipe()
        let writer = JSONLWriter(handle: pipe.fileHandleForWriting)
        let start = Message(id: "m_00000010", session: session, sender: .agent, seq: 1, time: "2026-11-12T10:00:00Z",
                            body: .runStarted(RunStarted(parentRunId: "m_00000009", toolCallId: "m_00000008",
                                                         agent: SubagentInfo(name: "revisor"))))
        let tool = Message(id: "m_00000011", session: session, sender: .agent, seq: 2, time: "2026-11-12T10:00:01Z",
                           body: .toolStart(ToolStart(runId: "m_00000010", name: "run_command",
                                                      arguments: ["argv": ["npm", "test"]], approvalId: "m_00000007")))
        try writer.write(start)
        try writer.write(tool)
        try pipe.fileHandleForWriting.close()
        let reader = JSONLReader(handle: pipe.fileHandleForReading)
        XCTAssertEqual(try reader.readAll(), [start, tool])
    }

    func testLectorSaltaLineasVaciasYLeeLaUltimaSinSalto() throws {
        let pipe = Pipe()
        let close = """
        {"pacai":"0.3","id":"m_00000001","type":"close","session":"\(session)","sender":"client","seq":1,"time":"2026-11-12T10:00:00Z","payload":{}}
        """
        pipe.fileHandleForWriting.write(Data(("\n\n" + close + "\n\n" + close.replacingOccurrences(of: "m_00000001", with: "m_00000002")).utf8))
        try pipe.fileHandleForWriting.close()
        let ids = try JSONLReader(handle: pipe.fileHandleForReading).readAll().map(\.id)
        XCTAssertEqual(ids, ["m_00000001", "m_00000002"])
    }

    func testLimiteDeTamano() throws {
        let pipe = Pipe()
        pipe.fileHandleForWriting.write(Data((String(repeating: "x", count: 4096) + "\n").utf8))
        try pipe.fileHandleForWriting.close()
        XCTAssertThrowsError(try JSONLReader(handle: pipe.fileHandleForReading, maxBytes: 1024).next())
    }

    func testCodificacionCompactaSinBarrasEscapadas() throws {
        let m = Message(id: "m_00000001", session: session, sender: .client, seq: 1, time: "2026-11-12T10:00:00Z",
                        body: .input(Input(blocks: [.text("ver https://a/b\nfin")])))
        let text = String(decoding: try JSONL.encode(m), as: UTF8.self)
        XCTAssertTrue(text.contains("https://a/b"))
        XCTAssertFalse(text.dropLast().contains("\n"))
        XCTAssertFalse(text.contains(": "))
    }

    func testValorNullEnUnParche() throws {
        let line = """
        {"pacai":"0.3","id":"m_00000001","type":"state_delta","session":"\(session)","sender":"client","seq":1,\
        "time":"2026-11-12T10:00:00Z","payload":{"patch":[{"op":"replace","path":"/client/busy","value":null}]}}
        """
        XCTAssertEqual(try object(JSONL.encode(JSONL.decode(line))), try object(Data(line.utf8)))
    }
}
