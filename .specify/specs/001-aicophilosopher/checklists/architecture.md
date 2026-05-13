# Architecture Compliance Checklist

このチェックリストは実装時・PRレビュー時に **必ず** 使用する。

## Acceptance Criteria (All must be satisfied)

### 1. Clean Architecture / Ports & Adapters
- [ ] `domain/`, `application/`, `ports/`, `infrastructure/adapters/`, `presentation/` の5層構造が守られている
- [ ] すべての外部依存（Gemini SDK, VectorDB, FileSystem, Search API など）は **Adapter** を介してのみアクセスされている
- [ ] LangGraph は `application/` 層のオーケストレーション基盤として直接使用されている（Adapter 化は不要）
- [ ] Domain 層は一切の外部ライブラリに依存していない（pure Python + Pydantic v2 のみ）
- [ ] 依存の方向が「内側 → 外側」のみ（Dependency Inversion Principle 遵守）

### 2. Type Safety
- [ ] すべての public クラス・関数・ポートに **型ヒント** が完全についている
- [ ] Pydantic v2 (`BaseModel`, `TypeAdapter`) / `typing.Protocol` を適切に使用している
- [ ] `mypy --strict` または `pyright --strict` で **エラー0** である
- [ ] ランタイムでも `model_validate` / `TypeAdapter` などで検証されている

### 3. Maintainability & Testability
- [ ] Ports ごとにユニットテストが書かれている（または書ける構造になっている）
- [ ] Adapter の入れ替えが1箇所（config / DIコンテナ）で可能
- [ ] 循環参照が存在しない（`ruff check` + `pyright` で検出済み）

### 4. AI Co-Philosopher 特有の要件
- [ ] Uncertainty Registry, Dialectical History, Working Paper は **domain/entity** として定義されている
- [ ] Project Coordinator と Workstream Coordinators は LangGraph の subgraph として実装されている
- [ ] すべてのエージェント間通信は Ports を通して行われている
- [ ] Agent / Coordinator は直接ファイルシステムやデータベースを操作していない（StoragePort 経由）

**違反が発見された場合**: PR は即マージ禁止。修正必須。
