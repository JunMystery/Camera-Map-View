"""Application translations and runtime language selection."""

from typing import Any

DEFAULT_LANGUAGE = "vi"
SUPPORTED_LANGUAGES = ("vi", "en", "jp")

LANGUAGE_LABELS = {
    "vi": "Tiếng Việt",
    "en": "English",
    "jp": "日本語",
}

_current_language = DEFAULT_LANGUAGE

TRANSLATIONS: dict[str, dict[str, str]] = {
    "app.title": {
        "vi": "Camera Map Manager",
        "en": "Camera Map Manager",
        "jp": "カメラマップ管理",
    },
    "app.ready": {
        "vi": "Sẵn sàng. Kéo thả camera lên bản đồ để định vị.",
        "en": "Ready. Drag cameras onto the map to position them.",
        "jp": "準備完了。カメラを地図へドラッグして配置してください。",
    },
    "dock.control_panel": {
        "vi": "Bảng Điều Khiển",
        "en": "Control Panel",
        "jp": "コントロールパネル",
    },
    "dock.drawing_tools": {
        "vi": "Công cụ vẽ",
        "en": "Drawing Tools",
        "jp": "描画ツール",
    },
    "dock.layers": {
        "vi": "Layers",
        "en": "Layers",
        "jp": "レイヤー",
    },
    "dock.layouts": {
        "vi": "Sơ đồ",
        "en": "Layouts",
        "jp": "レイアウト",
    },
    "widgets.panels": {
        "vi": "Mở bảng điều khiển",
        "en": "Open panels",
        "jp": "パネルを開く",
    },
    "action.open_map": {
        "vi": "Tải bản đồ nền...",
        "en": "Load background map...",
        "jp": "背景マップを読み込む...",
    },
    "action.unload_map": {
        "vi": "Gỡ bản đồ nền",
        "en": "Unload background map",
        "jp": "背景マップを解除",
    },
    "action.exit": {
        "vi": "Thoát",
        "en": "Exit",
        "jp": "終了",
    },
    "action.settings": {
        "vi": "Cài đặt",
        "en": "Settings",
        "jp": "設定",
    },
    "action.zoom_in": {
        "vi": "Phóng to",
        "en": "Zoom in",
        "jp": "拡大",
    },
    "action.zoom_out": {
        "vi": "Thu nhỏ",
        "en": "Zoom out",
        "jp": "縮小",
    },
    "action.zoom_fit": {
        "vi": "Căn vừa màn hình",
        "en": "Fit to window",
        "jp": "画面に合わせる",
    },
    "action.select": {
        "vi": "Chọn",
        "en": "Select",
        "jp": "選択",
    },
    "action.draw_line": {
        "vi": "Vẽ đường",
        "en": "Draw line",
        "jp": "線を描く",
    },
    "action.draw_rectangle": {
        "vi": "Vẽ khung",
        "en": "Draw rectangle",
        "jp": "四角形を描く",
    },
    "action.draw_zone": {
        "vi": "Vẽ vùng",
        "en": "Draw zone",
        "jp": "ゾーンを描く",
    },
    "action.draw_freehand": {
        "vi": "Vẽ tự do",
        "en": "Freehand",
        "jp": "フリーハンド",
    },
    "action.add_text": {
        "vi": "Thêm chữ",
        "en": "Add text",
        "jp": "テキスト追加",
    },
    "action.insert_png": {
        "vi": "Chèn PNG",
        "en": "Insert PNG",
        "jp": "PNG挿入",
    },
    "action.choose_color": {
        "vi": "Chọn màu",
        "en": "Choose color",
        "jp": "色を選択",
    },
    "action.delete_selected": {
        "vi": "Xóa đã chọn",
        "en": "Delete selected",
        "jp": "選択項目を削除",
    },
    "action.rotate_camera": {
        "vi": "Xoay camera",
        "en": "Rotate camera",
        "jp": "カメラ回転",
    },
    "action.toggle_grid": {
        "vi": "Ẩn/Hiện lưới",
        "en": "Show grid",
        "jp": "グリッド表示",
    },
    "action.show_name": {
        "vi": "Tên",
        "en": "Name",
        "jp": "名前",
    },
    "action.show_zone": {
        "vi": "Vùng",
        "en": "Zone",
        "jp": "ゾーン",
    },
    "action.show_ip": {
        "vi": "IP",
        "en": "IP",
        "jp": "IP",
    },
    "action.show_dvr": {
        "vi": "DVR gốc",
        "en": "Source DVR",
        "jp": "元DVR",
    },
    "menu.file": {
        "vi": "Tệp tin",
        "en": "File",
        "jp": "ファイル",
    },
    "menu.view": {
        "vi": "Hiển thị",
        "en": "View",
        "jp": "表示",
    },
    "menu.draw": {
        "vi": "Vẽ",
        "en": "Draw",
        "jp": "描画",
    },
    "menu.annotate": {
        "vi": "Chú thích",
        "en": "Annotate",
        "jp": "注釈",
    },
    "menu.tools": {
        "vi": "Công cụ",
        "en": "Tools",
        "jp": "ツール",
    },
    "menu.language": {
        "vi": "Ngôn ngữ",
        "en": "Language",
        "jp": "言語",
    },
    "toolbar.main": {
        "vi": "Thanh công cụ chính",
        "en": "Main toolbar",
        "jp": "メインツールバー",
    },
    "layer.background": {
        "vi": "Bản đồ nền",
        "en": "Background",
        "jp": "背景",
    },
    "layer.grid": {
        "vi": "Lưới",
        "en": "Grid",
        "jp": "グリッド",
    },
    "layer.cameras": {
        "vi": "Camera",
        "en": "Cameras",
        "jp": "カメラ",
    },
    "layer.drawings": {
        "vi": "Hình vẽ",
        "en": "Drawings",
        "jp": "描画",
    },
    "layer.images": {
        "vi": "Hình ảnh",
        "en": "Images",
        "jp": "画像",
    },
    "layer.text": {
        "vi": "Chữ",
        "en": "Text",
        "jp": "テキスト",
    },
    "layer.visible": {
        "vi": "Hiện",
        "en": "Show",
        "jp": "表示",
    },
    "layer.active": {
        "vi": "Vẽ",
        "en": "Draw",
        "jp": "描画",
    },
    "layer.locked": {
        "vi": "Khóa",
        "en": "Lock",
        "jp": "ロック",
    },
    "layer.name": {
        "vi": "Tên",
        "en": "Name",
        "jp": "名前",
    },
    "layer.count": {
        "vi": "Số lượng",
        "en": "Count",
        "jp": "数",
    },
    "layer.add": {
        "vi": "Thêm layer",
        "en": "Add layer",
        "jp": "レイヤー追加",
    },
    "layer.new": {
        "vi": "Layer",
        "en": "Layer",
        "jp": "レイヤー",
    },
    "layer.select": {
        "vi": "Chọn",
        "en": "Select",
        "jp": "選択",
    },
    "layer.delete": {
        "vi": "Xóa",
        "en": "Delete",
        "jp": "削除",
    },
    "layer.up": {
        "vi": "Lên",
        "en": "Up",
        "jp": "上",
    },
    "layer.down": {
        "vi": "Xuống",
        "en": "Down",
        "jp": "下",
    },
    "layer.move_selected": {
        "vi": "Chuyển vào layer",
        "en": "Move selected",
        "jp": "選択項目を移動",
    },
    "layer.delete_confirm": {
        "vi": "Layer này có đối tượng. Xóa layer sẽ xóa luôn các đối tượng bên trong. Tiếp tục?",
        "en": "This layer contains objects. Deleting it will also delete those objects. Continue?",
        "jp": "このレイヤーにはオブジェクトがあります。削除すると中のオブジェクトも削除されます。続行しますか？",
    },
    "layout.add": {
        "vi": "Thêm",
        "en": "Add",
        "jp": "追加",
    },
    "layout.rename": {
        "vi": "Sửa",
        "en": "Rename",
        "jp": "名前変更",
    },
    "layout.delete": {
        "vi": "Xóa",
        "en": "Delete",
        "jp": "削除",
    },
    "layout.name": {
        "vi": "Tên sơ đồ",
        "en": "Layout name",
        "jp": "レイアウト名",
    },
    "dialog.choose_map.title": {
        "vi": "Chọn ảnh sơ đồ mặt bằng",
        "en": "Choose floor plan image",
        "jp": "フロア図画像を選択",
    },
    "dialog.choose_map.filter": {
        "vi": "Hình ảnh (*.png *.jpg *.jpeg *.bmp)",
        "en": "Images (*.png *.jpg *.jpeg *.bmp)",
        "jp": "画像 (*.png *.jpg *.jpeg *.bmp)",
    },
    "dialog.choose_png.title": {
        "vi": "Chọn ảnh PNG",
        "en": "Choose PNG image",
        "jp": "PNG画像を選択",
    },
    "dialog.choose_png.filter": {
        "vi": "PNG (*.png)",
        "en": "PNG (*.png)",
        "jp": "PNG (*.png)",
    },
    "dialog.choose_csv.title": {
        "vi": "Chọn file CSV camera",
        "en": "Choose camera CSV",
        "jp": "カメラCSVを選択",
    },
    "dialog.choose_csv.filter": {
        "vi": "CSV (*.csv)",
        "en": "CSV (*.csv)",
        "jp": "CSV (*.csv)",
    },
    "dialog.save_csv.title": {
        "vi": "Lưu file CSV camera",
        "en": "Save camera CSV",
        "jp": "カメラCSVを保存",
    },
    "settings.title": {
        "vi": "Cài đặt",
        "en": "Settings",
        "jp": "設定",
    },
    "settings.network": {
        "vi": "Mạng",
        "en": "Network",
        "jp": "ネットワーク",
    },
    "settings.canvas": {
        "vi": "Canvas",
        "en": "Canvas",
        "jp": "キャンバス",
    },
    "settings.appearance": {
        "vi": "Giao diện",
        "en": "Appearance",
        "jp": "外観",
    },
    "settings.ping_interval": {
        "vi": "Chu kỳ ping (giây)",
        "en": "Ping interval (seconds)",
        "jp": "Ping間隔（秒）",
    },
    "settings.timeout": {
        "vi": "Timeout (giây)",
        "en": "Timeout (seconds)",
        "jp": "タイムアウト（秒）",
    },
    "settings.retries": {
        "vi": "Số lần thử lại",
        "en": "Retries",
        "jp": "再試行回数",
    },
    "settings.canvas_width": {
        "vi": "Chiều rộng canvas",
        "en": "Canvas width",
        "jp": "キャンバス幅",
    },
    "settings.canvas_height": {
        "vi": "Chiều cao canvas",
        "en": "Canvas height",
        "jp": "キャンバス高さ",
    },
    "settings.grid_size": {
        "vi": "Kích thước grid",
        "en": "Grid size",
        "jp": "グリッドサイズ",
    },
    "settings.background_scale": {
        "vi": "Tỉ lệ bản đồ nền",
        "en": "Background scale",
        "jp": "背景スケール",
    },
    "settings.light_theme": {
        "vi": "Light theme",
        "en": "Light theme",
        "jp": "ライトテーマ",
    },
    "dialog.add_text.title": {
        "vi": "Thêm chữ",
        "en": "Add text",
        "jp": "テキスト追加",
    },
    "dialog.add_text.label": {
        "vi": "Nội dung",
        "en": "Text",
        "jp": "テキスト",
    },
    "dialog.add_text.size": {
        "vi": "Kích thước",
        "en": "Size",
        "jp": "サイズ",
    },
    "dialog.add_text.color": {
        "vi": "Màu sắc",
        "en": "Color",
        "jp": "色",
    },
    "dialog.edit_text.title": {
        "vi": "Sửa chữ",
        "en": "Edit text",
        "jp": "テキスト編集",
    },
    "dialog.choose_color.title": {
        "vi": "Chọn màu vẽ",
        "en": "Choose drawing color",
        "jp": "描画色を選択",
    },
    "dialog.confirm_unload_map.title": {
        "vi": "Gỡ bản đồ nền?",
        "en": "Unload background map?",
        "jp": "背景マップを解除しますか？",
    },
    "dialog.confirm_unload_map.body": {
        "vi": "Bản đồ nền hiện tại sẽ bị gỡ khỏi canvas. Tiếp tục?",
        "en": "The current background map will be removed from the canvas. Continue?",
        "jp": "現在の背景マップがキャンバスから削除されます。続行しますか？",
    },
    "dialog.confirm_exit.title": {
        "vi": "Thoát ứng dụng?",
        "en": "Exit application?",
        "jp": "アプリを終了しますか？",
    },
    "dialog.confirm_exit.body": {
        "vi": "Bạn có chắc muốn thoát ứng dụng?",
        "en": "Are you sure you want to exit the application?",
        "jp": "アプリケーションを終了してもよろしいですか？",
    },
    "error.load_file.title": {
        "vi": "Lỗi tải tệp",
        "en": "File load error",
        "jp": "ファイル読み込みエラー",
    },
    "error.load_file.body": {
        "vi": "Không thể tải tệp hình ảnh được chọn hoặc tệp hình ảnh không hợp lệ.",
        "en": "The selected image could not be loaded or is not a valid image file.",
        "jp": "選択した画像を読み込めないか、画像ファイルが無効です。",
    },
    "status.map_loaded": {
        "vi": "Đã tải bản đồ: {filename}",
        "en": "Loaded map: {filename}",
        "jp": "マップを読み込みました: {filename}",
    },
    "status.map_unloaded": {
        "vi": "Đã gỡ bản đồ nền.",
        "en": "Unloaded background map.",
        "jp": "背景マップを解除しました。",
    },
    "camera_panel.title": {
        "vi": "Danh sách Camera Chưa Đặt",
        "en": "Unplaced Cameras",
        "jp": "未配置カメラ",
    },
    "camera_panel.title_unplaced": {
        "vi": "Danh sách camera chưa đặt",
        "en": "Unplaced Cameras",
        "jp": "未配置カメラ",
    },
    "camera_panel.title_placed": {
        "vi": "Danh sách camera đã đặt",
        "en": "Placed Cameras",
        "jp": "配置済みカメラ",
    },
    "camera_panel.search": {
        "vi": "Tìm theo tên, IP, DVR, vùng...",
        "en": "Search name, IP, DVR, zone...",
        "jp": "名前、IP、DVR、ゾーンで検索...",
    },
    "camera_panel.unplaced": {
        "vi": "Chưa đặt",
        "en": "Unplaced",
        "jp": "未配置",
    },
    "camera_panel.placed": {
        "vi": "Đã đặt",
        "en": "Placed",
        "jp": "配置済み",
    },
    "camera_panel.add": {
        "vi": "Thêm",
        "en": "Add",
        "jp": "追加",
    },
    "camera_panel.edit": {
        "vi": "Sửa",
        "en": "Edit",
        "jp": "編集",
    },
    "camera_panel.delete": {
        "vi": "Xóa",
        "en": "Delete",
        "jp": "削除",
    },
    "camera_panel.import": {
        "vi": "Nhập CSV",
        "en": "Import CSV",
        "jp": "CSV取込",
    },
    "camera_panel.export": {
        "vi": "Xuất CSV",
        "en": "Export CSV",
        "jp": "CSV出力",
    },
    "camera_panel.no_dvr": {
        "vi": "Chưa gán DVR",
        "en": "No DVR",
        "jp": "DVR未設定",
    },
    "camera_panel.item": {
        "vi": "📹 {name}\n({ip_address})",
        "en": "📹 {name}\n({ip_address})",
        "jp": "📹 {name}\n({ip_address})",
    },
    "dashboard.total": {
        "vi": "Tổng: {total}",
        "en": "Total: {total}",
        "jp": "合計: {total}",
    },
    "dashboard.online": {
        "vi": "Online: {online}",
        "en": "Online: {online}",
        "jp": "オンライン: {online}",
    },
    "dashboard.offline": {
        "vi": "Offline: {offline}",
        "en": "Offline: {offline}",
        "jp": "オフライン: {offline}",
    },
    "camera.status.online": {
        "vi": "Online",
        "en": "Online",
        "jp": "オンライン",
    },
    "camera.status.offline": {
        "vi": "Offline",
        "en": "Offline",
        "jp": "オフライン",
    },
    "camera.tooltip": {
        "vi": "Tên: {name}\nVùng: {zone}\nIP: {ip_address}:{port}\nDVR gốc: {dvr_origin}\nLoại: {camera_type}\nGóc: {rotation}°\nTrạng thái: {status}\nGhi chú: {notes}",
        "en": "Name: {name}\nZone: {zone}\nIP: {ip_address}:{port}\nSource DVR: {dvr_origin}\nType: {camera_type}\nRotation: {rotation}°\nStatus: {status}\nNotes: {notes}",
        "jp": "名前: {name}\nゾーン: {zone}\nIP: {ip_address}:{port}\n元DVR: {dvr_origin}\n種類: {camera_type}\n回転: {rotation}°\n状態: {status}\nメモ: {notes}",
    },
    "camera.notes.empty": {
        "vi": "Không có",
        "en": "None",
        "jp": "なし",
    },
    "camera.context.edit": {
        "vi": "Chỉnh sửa thông số",
        "en": "Edit properties",
        "jp": "プロパティを編集",
    },
    "camera_dialog.title": {
        "vi": "Thuộc tính Camera",
        "en": "Camera Properties",
        "jp": "カメラプロパティ",
    },
    "camera_dialog.name": {
        "vi": "Tên camera",
        "en": "Camera name",
        "jp": "カメラ名",
    },
    "camera_dialog.ip": {
        "vi": "IP Address",
        "en": "IP Address",
        "jp": "IPアドレス",
    },
    "camera_dialog.port": {
        "vi": "Cổng RTSP",
        "en": "RTSP port",
        "jp": "RTSPポート",
    },
    "camera_dialog.type": {
        "vi": "Loại camera",
        "en": "Camera type",
        "jp": "カメラ種別",
    },
    "camera_dialog.zone": {
        "vi": "Vùng",
        "en": "Zone",
        "jp": "ゾーン",
    },
    "camera_dialog.dvr_origin": {
        "vi": "DVR gốc",
        "en": "Source DVR",
        "jp": "元DVR",
    },
    "camera_dialog.rotation": {
        "vi": "Góc quay",
        "en": "Rotation",
        "jp": "回転角度",
    },
    "camera_dialog.status": {
        "vi": "Trạng thái",
        "en": "Status",
        "jp": "状態",
    },
    "camera_dialog.notes": {
        "vi": "Ghi chú",
        "en": "Notes",
        "jp": "メモ",
    },
    "camera_dialog.save": {
        "vi": "Lưu",
        "en": "Save",
        "jp": "保存",
    },
    "camera_dialog.cancel": {
        "vi": "Hủy",
        "en": "Cancel",
        "jp": "キャンセル",
    },
    "camera_type.fixed": {
        "vi": "Cố định",
        "en": "Fixed",
        "jp": "固定",
    },
    "camera_type.ptz": {
        "vi": "PTZ",
        "en": "PTZ",
        "jp": "PTZ",
    },
    "camera_type.dome": {
        "vi": "Dome",
        "en": "Dome",
        "jp": "ドーム",
    },
    "camera_type.fisheye": {
        "vi": "Fisheye",
        "en": "Fisheye",
        "jp": "魚眼",
    },
    "camera_type.360": {
        "vi": "360 độ",
        "en": "360-degree",
        "jp": "360度",
    },
    "camera_type.ai": {
        "vi": "AI",
        "en": "AI",
        "jp": "AI",
    },
    "validation.camera_name_required": {
        "vi": "Tên camera không được để trống.",
        "en": "Camera name is required.",
        "jp": "カメラ名は必須です。",
    },
    "validation.invalid_ip": {
        "vi": "IP không hợp lệ.",
        "en": "Invalid IP address.",
        "jp": "IPアドレスが無効です。",
    },
    "status.camera_placed": {
        "vi": "Đã đặt camera '{name}' tại tọa độ ({x}, {y})",
        "en": "Placed camera '{name}' at ({x}, {y})",
        "jp": "カメラ「{name}」を座標 ({x}, {y}) に配置しました",
    },
    "status.camera_ping": {
        "vi": "Camera {camera_id}: {status} ({latency_ms:.1f} ms)",
        "en": "Camera {camera_id}: {status} ({latency_ms:.1f} ms)",
        "jp": "カメラ {camera_id}: {status} ({latency_ms:.1f} ms)",
    },
    "status.camera_update_failed": {
        "vi": "Không thể cập nhật camera. IP có thể đã bị trùng.",
        "en": "Could not update camera. The IP may already be in use.",
        "jp": "カメラを更新できません。IPが既に使用されている可能性があります。",
    },
    "status.camera_updated": {
        "vi": "Đã cập nhật camera '{name}'.",
        "en": "Updated camera '{name}'.",
        "jp": "カメラ「{name}」を更新しました。",
    },
    "status.drawing_deleted": {
        "vi": "Đã xóa {count} đối tượng.",
        "en": "Deleted {count} item(s).",
        "jp": "{count} 件を削除しました。",
    },
    "status.camera_rotated": {
        "vi": "Đã xoay {count} camera.",
        "en": "Rotated {count} camera(s).",
        "jp": "{count} 台のカメラを回転しました。",
    },
    "status.png_inserted": {
        "vi": "Đã chèn ảnh PNG.",
        "en": "Inserted PNG image.",
        "jp": "PNG画像を挿入しました。",
    },
    "status.csv_imported": {
        "vi": "Đã nhập {count} camera từ CSV.",
        "en": "Imported {count} camera(s) from CSV.",
        "jp": "CSVから {count} 台のカメラを取り込みました。",
    },
    "status.csv_exported": {
        "vi": "Đã xuất CSV camera.",
        "en": "Exported camera CSV.",
        "jp": "カメラCSVを出力しました。",
    },
    "status.layer_selected": {
        "vi": "Đã chọn {count} đối tượng trong layer.",
        "en": "Selected {count} layer item(s).",
        "jp": "レイヤー内の {count} 件を選択しました。",
    },
    "status.layer_deleted": {
        "vi": "Đã xóa {count} đối tượng trong layer.",
        "en": "Deleted {count} layer item(s).",
        "jp": "レイヤー内の {count} 件を削除しました。",
    },
    "status.layer_moved": {
        "vi": "Đã chuyển {count} đối tượng vào layer.",
        "en": "Moved {count} item(s) into the layer.",
        "jp": "{count} 件をレイヤーへ移動しました。",
    },
    "status.layer_camera_delete_blocked": {
        "vi": "Không xóa hàng loạt camera từ layer để tránh mất dữ liệu.",
        "en": "Bulk camera deletion from layers is disabled to protect data.",
        "jp": "データ保護のため、レイヤーからのカメラ一括削除は無効です。",
    },
    "seed.cam_01.name": {
        "vi": "Cổng Chính (Main Gate)",
        "en": "Main Gate",
        "jp": "正門",
    },
    "seed.cam_01.notes": {
        "vi": "Góc nhìn bãi xe chính",
        "en": "Main parking lot view",
        "jp": "メイン駐車場の視野",
    },
    "seed.cam_02.name": {
        "vi": "Quầy Lễ Tân (Reception)",
        "en": "Reception",
        "jp": "受付",
    },
    "seed.cam_02.notes": {
        "vi": "Khu vực sảnh đón khách",
        "en": "Guest reception lobby",
        "jp": "来客受付ロビー",
    },
    "seed.cam_03.name": {
        "vi": "Phòng Server (Server Room)",
        "en": "Server Room",
        "jp": "サーバールーム",
    },
    "seed.cam_03.notes": {
        "vi": "Hạn chế ra vào",
        "en": "Restricted access",
        "jp": "入退室制限あり",
    },
    "seed.cam_04.name": {
        "vi": "Bãi Xe Nội Bộ (Internal Parking)",
        "en": "Internal Parking",
        "jp": "社内駐車場",
    },
    "seed.cam_04.notes": {
        "vi": "Camera xoay quét 360 độ",
        "en": "360-degree pan camera",
        "jp": "360度パンカメラ",
    },
    "seed.cam_05.name": {
        "vi": "Nhà Kho (Warehouse)",
        "en": "Warehouse",
        "jp": "倉庫",
    },
    "seed.cam_05.notes": {
        "vi": "Camera giám sát lưu kho",
        "en": "Warehouse monitoring camera",
        "jp": "倉庫監視カメラ",
    },
}


def set_language(language: str) -> None:
    """Set the active application language."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    global _current_language
    _current_language = language


def get_language() -> str:
    """Return the active application language."""
    return _current_language


def t(key: str, **placeholders: Any) -> str:
    """Translate a key and apply placeholder values."""
    translations = TRANSLATIONS.get(key)
    if translations is None:
        raise KeyError(f"Missing translation key: {key}")
    template = translations.get(_current_language) or translations[DEFAULT_LANGUAGE]
    return template.format(**placeholders)
