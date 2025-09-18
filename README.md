# MCP Tutorial - WebSocket Demo

## 概要

MCP（Model Context Protocol）ライクなWebSocketサーバーのデモアプリケーションです。FastAPIを使用してWebSocketサーバーを構築し、ブラウザからツール呼び出し機能をテストできます。

## 機能

- **WebSocketサーバー**: FastAPIベースのリアルタイム通信
- **ツールカタログ**: 利用可能なツールの一覧を提供
- **検索ツール**: ダミーの検索機能（クエリに対してサンプル結果を返却）
- **ブラウザテスター**: HTMLクライアントでリアルタイムにツール呼び出しをテスト
- **リクエスト追跡**: 各ツール呼び出しのライフサイクルを可視化

## アーキテクチャ

```
┌─────────────────┐    WebSocket    ┌──────────────────┐
│   ブラウザ      │ ←──────────────→ │   FastAPIサーバー│
│  (HTMLクライアント)│                   │    (main.py)     │
└─────────────────┘                   └──────────────────┘
```

## メッセージフロー

1. **カタログ要求** (`catalog_request`) → **カタログ応答** (`catalog`)
2. **ツール呼び出し** (`tool_call`) → **受理ACK** (`tool_ack`) → **部分結果** (`partial_result`) → **完了** (`complete`)

## 使用方法

### サーバー起動
```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

### ブラウザでテスト
1. `http://localhost:8000` にアクセス
2. "Get Catalog"ボタンでツール一覧を取得
3. 検索クエリを入力して"Call search"でツール実行
4. リアルタイムで結果とログを確認

## 技術仕様

- **フレームワーク**: FastAPI
- **プロトコル**: WebSocket
- **ツール**: search（ダミー検索機能）
- **フロントエンド**: Vanilla JavaScript
- **メッセージ形式**: JSON

## ファイル構成

- `main.py`: サーバー本体（WebSocket・REST API・HTMLクライアント）
