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
        "vi": "Sẵn sàng. Kéo thả thiết bị lên bản đồ để định vị.",
        "en": "Ready. Drag devices onto the map to position them.",
        "jp": "準備完了。デバイスを地図へドラッグして配置してください。",
    },
    "status.no_layout": {
        "vi": "Chưa có sơ đồ. Hãy tạo sơ đồ mới hoặc nhập file .cmvmap để sử dụng.",
        "en": "No layout is available. Create a new layout or import a .cmvmap file to continue.",
        "jp": "レイアウトがありません。続行するには新しいレイアウトを作成するか、.cmvmap ファイルをインポートしてください。",
    },
    "button.yes": {
        "vi": "Có",
        "en": "Yes",
        "jp": "はい",
    },
    "button.no": {
        "vi": "Không",
        "en": "No",
        "jp": "いいえ",
    },
    "button.close": {
        "vi": "Dong",
        "en": "Close",
        "jp": "Close",
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
    "action.import_package": {
        "vi": "Nhập sơ đồ...",
        "en": "Import diagram...",
        "jp": "図面をインポート...",
    },
    "action.export_package": {
        "vi": "Xuất sơ đồ...",
        "en": "Export diagram...",
        "jp": "図面をエクスポート...",
    },
    "action.undo": {
        "vi": "Hoàn tác",
        "en": "Undo",
        "jp": "元に戻す",
    },
    "action.redo": {
        "vi": "Làm lại",
        "en": "Redo",
        "jp": "やり直す",
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
    "action.pan": {
        "vi": "Di chuyển bản đồ",
        "en": "Pan map",
        "jp": "地図をパン",
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
    "menu.action": {
        "vi": "Thao tác",
        "en": "Action",
        "jp": "アクション",
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
        "vi": "Thiết bị",
        "en": "Devices",
        "jp": "デバイス",
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
    "layer.expand": {
        "vi": "Mở layer",
        "en": "Expand layer",
        "jp": "レイヤーを展開",
    },
    "layer.collapse": {
        "vi": "Thu gọn layer",
        "en": "Collapse layer",
        "jp": "レイヤーを折りたたむ",
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
    "layout.edit": {
        "vi": "Chỉnh sửa sơ đồ",
        "en": "Edit layout",
        "jp": "レイアウト編集",
    },
    "layout.delete": {
        "vi": "Xóa",
        "en": "Delete",
        "jp": "削除",
    },
    "layout.create_title": {
        "vi": "Tạo sơ đồ",
        "en": "Create layout",
        "jp": "レイアウト作成",
    },
    "layout.edit_title": {
        "vi": "Chỉnh sửa sơ đồ",
        "en": "Edit layout",
        "jp": "レイアウト編集",
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
    "dialog.choose_location_image.title": {
        "vi": "Chọn ảnh vị trí camera",
        "en": "Choose camera location image",
        "jp": "カメラ位置画像を選択",
    },
    "dialog.image.filter": {
        "vi": "Hình ảnh (*.png *.jpg *.jpeg *.bmp *.webp);;Tất cả tệp (*.*)",
        "en": "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All files (*.*)",
        "jp": "画像 (*.png *.jpg *.jpeg *.bmp *.webp);;すべてのファイル (*.*)",
    },
    "dialog.choose_csv.title": {
        "vi": "Chọn file CSV thiết bị",
        "en": "Choose device CSV",
        "jp": "デバイスCSVを選択",
    },
    "dialog.choose_csv.filter": {
        "vi": "CSV (*.csv)",
        "en": "CSV (*.csv)",
        "jp": "CSV (*.csv)",
    },
    "dialog.save_csv.title": {
        "vi": "Lưu file CSV thiết bị",
        "en": "Save device CSV",
        "jp": "デバイスCSVを保存",
    },
    "dialog.choose_package.title": {
        "vi": "Chọn file sơ đồ",
        "en": "Choose diagram package",
        "jp": "図面パッケージを選択",
    },
    "dialog.save_package.title": {
        "vi": "Lưu file sơ đồ",
        "en": "Save diagram package",
        "jp": "図面パッケージを保存",
    },
    "dialog.package.filter": {
        "vi": "Camera Map (*.cmvmap)",
        "en": "Camera Map (*.cmvmap)",
        "jp": "Camera Map (*.cmvmap)",
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
    "settings.theme": {
        "vi": "Giao diện",
        "en": "Theme",
        "jp": "テーマ",
    },
    "settings.theme_dark": {
        "vi": "Tối",
        "en": "Dark",
        "jp": "ダーク",
    },
    "settings.theme_light": {
        "vi": "Sáng",
        "en": "Light",
        "jp": "ライト",
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
    "dialog.confirm_delete_layout.title": {
        "vi": "Xóa sơ đồ?",
        "en": "Delete layout?",
        "jp": "レイアウトを削除しますか？",
    },
    "dialog.confirm_delete_layout.body": {
        "vi": "Bạn có chắc muốn xóa sơ đồ '{name}'? Tất cả thiết bị, layer và hình vẽ trong sơ đồ này sẽ bị xóa.",
        "en": "Delete layout '{name}'? All devices, layers, and drawings in this layout will be removed.",
        "jp": "レイアウト「{name}」を削除しますか？このレイアウト内のデバイス、レイヤー、描画はすべて削除されます。",
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
    "error.package.title": {
        "vi": "Lỗi file sơ đồ",
        "en": "Diagram package error",
        "jp": "図面パッケージエラー",
    },
    "error.package.body": {
        "vi": "Không thể nhập hoặc xuất file sơ đồ đã chọn.",
        "en": "Could not import or export the selected diagram package.",
        "jp": "選択した図面パッケージをインポートまたはエクスポートできません。",
    },
    "error.location_image_invalid": {
        "vi": "Không thể đọc ảnh vị trí đã chọn.",
        "en": "Could not read the selected location image.",
        "jp": "選択した位置画像を読み取れません。",
    },
    "error.location_image_missing.title": {
        "vi": "Không tìm thấy ảnh vị trí",
        "en": "Location image not found",
        "jp": "位置画像が見つかりません",
    },
    "error.location_image_missing.body": {
        "vi": "Ảnh vị trí của camera không tồn tại hoặc không thể mở.",
        "en": "The camera location image is missing or cannot be opened.",
        "jp": "カメラの位置画像が存在しないか開けません。",
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
    "status.package_exported": {
        "vi": "Đã xuất file sơ đồ.",
        "en": "Exported diagram package.",
        "jp": "図面パッケージをエクスポートしました。",
    },
    "status.package_imported": {
        "vi": "Đã nhập file sơ đồ.",
        "en": "Imported diagram package.",
        "jp": "図面パッケージをインポートしました。",
    },
    "camera_panel.title": {
        "vi": "Danh sách thiết bị chưa đặt",
        "en": "Unplaced Devices",
        "jp": "未配置デバイス",
    },
    "camera_panel.title_unplaced": {
        "vi": "Danh sách thiết bị chưa đặt",
        "en": "Unplaced Devices",
        "jp": "未配置デバイス",
    },
    "camera_panel.title_placed": {
        "vi": "Danh sách thiết bị đã đặt",
        "en": "Placed Devices",
        "jp": "配置済みデバイス",
    },
    "camera_panel.search": {
        "vi": "Tìm thiết bị theo tên, IP, DVR, vùng...",
        "en": "Search devices by name, IP, DVR, zone...",
        "jp": "名前、IP、DVR、ゾーンでデバイスを検索...",
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
    "camera_panel.online_group": {
        "vi": "Online",
        "en": "Online",
        "jp": "オンライン",
    },
    "camera_panel.offline_group": {
        "vi": "Offline",
        "en": "Offline",
        "jp": "オフライン",
    },
    "camera_panel.item": {
        "vi": "📹 {name}\n{device_kind} / {variant} / {ip_address}",
        "en": "📹 {name}\n{device_kind} / {variant} / {ip_address}",
        "jp": "📹 {name}\n{device_kind} / {variant} / {ip_address}",
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
    "camera.context.location_image": {
        "vi": "Ảnh vị trí",
        "en": "Location image",
        "jp": "位置画像",
    },
    "camera.context.ping": {
        "vi": "Ping",
        "en": "Ping",
        "jp": "Ping",
    },
    "camera_location_image.title": {
        "vi": "Ảnh vị trí - {name}",
        "en": "Location image - {name}",
        "jp": "位置画像 - {name}",
    },
    "camera_location_image.zoom_in": {
        "vi": "Phóng to",
        "en": "Zoom in",
        "jp": "拡大",
    },
    "camera_location_image.zoom_out": {
        "vi": "Thu nhỏ",
        "en": "Zoom out",
        "jp": "縮小",
    },
    "camera_location_image.fit": {
        "vi": "Căn vừa",
        "en": "Fit",
        "jp": "合わせる",
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
    "camera_dialog.fov": {
        "vi": "FOV",
        "en": "FOV",
        "jp": "FOV",
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
    "camera_dialog.location_image": {
        "vi": "Ảnh vị trí",
        "en": "Location image",
        "jp": "位置画像",
    },
    "camera_dialog.upload_location_image": {
        "vi": "Upload...",
        "en": "Upload...",
        "jp": "アップロード...",
    },
    "camera_dialog.remove_location_image": {
        "vi": "Xóa",
        "en": "Remove",
        "jp": "削除",
    },
    "camera_dialog.no_location_image": {
        "vi": "Chưa có ảnh",
        "en": "No image",
        "jp": "画像なし",
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
    "validation.device_name_required": {
        "vi": "Tên thiết bị không được để trống.",
        "en": "Device name is required.",
        "jp": "デバイス名は必須です。",
    },
    "validation.layout_name_required": {
        "vi": "Tên sơ đồ không được để trống.",
        "en": "Layout name is required.",
        "jp": "レイアウト名は必須です。",
    },
    "validation.invalid_ip": {
        "vi": "IP không hợp lệ.",
        "en": "Invalid IP address.",
        "jp": "IPアドレスが無効です。",
    },
    "status.camera_placed": {
        "vi": "Đã đặt thiết bị '{name}' tại tọa độ ({x}, {y})",
        "en": "Placed device '{name}' at ({x}, {y})",
        "jp": "デバイス「{name}」を座標 ({x}, {y}) に配置しました",
    },
    "status.camera_ping": {
        "vi": "Camera {camera_id}: {status} ({latency_ms:.1f} ms)",
        "en": "Camera {camera_id}: {status} ({latency_ms:.1f} ms)",
        "jp": "カメラ {camera_id}: {status} ({latency_ms:.1f} ms)",
    },
    "status.camera_update_failed": {
        "vi": "Không thể cập nhật thiết bị. IP có thể đã bị trùng.",
        "en": "Could not update device. The IP may already be in use.",
        "jp": "デバイスを更新できません。IPが既に使用されている可能性があります。",
    },
    "status.camera_updated": {
        "vi": "Đã cập nhật thiết bị '{name}'.",
        "en": "Updated device '{name}'.",
        "jp": "デバイス「{name}」を更新しました。",
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
    "status.location_image_missing": {
        "vi": "Camera '{name}' chưa có ảnh vị trí.",
        "en": "Camera '{name}' has no location image.",
        "jp": "カメラ「{name}」には位置画像がありません。",
    },
    "status.active_ping_started": {
        "vi": "Đã mở ping chủ động tới {ip_address}.",
        "en": "Started active ping to {ip_address}.",
        "jp": "{ip_address} へのアクティブPingを開始しました。",
    },
    "status.active_ping_failed": {
        "vi": "Không thể mở ping tới {ip_address}.",
        "en": "Could not start ping to {ip_address}.",
        "jp": "{ip_address} へのPingを開始できません。",
    },
    "status.undo_unavailable": {
        "vi": "Chưa có thao tác để hoàn tác.",
        "en": "No action is available to undo.",
        "jp": "元に戻す操作はありません。",
    },
    "status.redo_unavailable": {
        "vi": "Chưa có thao tác để làm lại.",
        "en": "No action is available to redo.",
        "jp": "やり直す操作はありません。",
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
    "action.link_device": {
        "vi": "Liên kết thiết bị",
        "en": "Link device",
        "jp": "デバイスをリンク",
    },
    "action.remove_device_link": {
        "vi": "Gỡ link thiết bị",
        "en": "Remove device link",
        "jp": "デバイスリンクを削除",
    },
    "camera_panel.add_device": {
        "vi": "Thêm thiết bị",
        "en": "Add device",
        "jp": "デバイスを追加",
    },
    "camera_panel.unknown_group": {
        "vi": "Unknown",
        "en": "Unknown",
        "jp": "不明",
    },
    "camera_panel.status_all": {
        "vi": "Tất cả",
        "en": "All",
        "jp": "すべて",
    },
    "camera_panel.unlinked_group": {
        "vi": "Chưa liên kết",
        "en": "Unlinked",
        "jp": "未リンク",
    },
    "device.ip_empty": {
        "vi": "Không có IP",
        "en": "No IP",
        "jp": "IPなし",
    },
    "device.status.unknown": {
        "vi": "Unknown",
        "en": "Unknown",
        "jp": "不明",
    },
    "device.ping.enabled": {
        "vi": "Bật",
        "en": "Enabled",
        "jp": "有効",
    },
    "device.ping.disabled": {
        "vi": "Tắt",
        "en": "Disabled",
        "jp": "無効",
    },
    "device.tooltip": {
        "vi": "Tên: {name}\nLoại: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nVùng: {zone}\nDVR gốc: {dvr_origin}\nGóc: {rotation}\nFOV: {fov_degrees}\nTrạng thái: {status}\nPing: {ping}\nGhi chú: {notes}",
        "en": "Name: {name}\nKind: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nZone: {zone}\nSource DVR: {dvr_origin}\nRotation: {rotation}\nFOV: {fov_degrees}\nStatus: {status}\nPing: {ping}\nNotes: {notes}",
        "jp": "名前: {name}\n種類: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nゾーン: {zone}\n元DVR: {dvr_origin}\n回転: {rotation}\nFOV: {fov_degrees}\n状態: {status}\nPing: {ping}\nメモ: {notes}",
    },
    "device.tooltip.generic": {
        "vi": "Tên: {name}\nLoại: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nVùng: {zone}\nDVR gốc: {dvr_origin}\nTrạng thái: {status}\nPing: {ping}\nGhi chú: {notes}",
        "en": "Name: {name}\nKind: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nZone: {zone}\nSource DVR: {dvr_origin}\nStatus: {status}\nPing: {ping}\nNotes: {notes}",
        "jp": "名前: {name}\n種類: {device_kind}\nVariant: {variant}\nIP: {ip_address}:{port}\nゾーン: {zone}\n元DVR: {dvr_origin}\n状態: {status}\nPing: {ping}\nメモ: {notes}",
    },
    "device_dialog.title": {
        "vi": "Thông số thiết bị",
        "en": "Device Properties",
        "jp": "デバイスプロパティ",
    },
    "device_dialog.name": {
        "vi": "Tên thiết bị",
        "en": "Device name",
        "jp": "デバイス名",
    },
    "device_dialog.kind": {
        "vi": "Loại thiết bị",
        "en": "Device kind",
        "jp": "デバイス種別",
    },
    "device_dialog.variant": {
        "vi": "Variant",
        "en": "Variant",
        "jp": "バリアント",
    },
    "device_dialog.ping_enabled": {
        "vi": "Ping thiết bị",
        "en": "Ping device",
        "jp": "デバイスをPing",
    },
    "device_dialog.links": {
        "vi": "Liên kết đến",
        "en": "Links to",
        "jp": "リンク先",
    },
    "device_dialog.connections": {
        "vi": "Kết nối",
        "en": "Connections",
        "jp": "接続",
    },
    "device_dialog.manage_connections": {
        "vi": "Quản lý kết nối",
        "en": "Manage connections",
        "jp": "接続を管理",
    },
    "device_dialog.linked_from": {
        "vi": "Được kết nối bởi",
        "en": "Linked from",
        "jp": "リンク元",
    },
    "device_connections.title": {
        "vi": "Quản lý kết nối: {name}",
        "en": "Manage connections: {name}",
        "jp": "接続を管理: {name}",
    },
    "device_connections.links_to": {
        "vi": "Kết nối đến",
        "en": "Links to",
        "jp": "接続先",
    },
    "device_connections.linked_from": {
        "vi": "Được kết nối bởi",
        "en": "Linked from",
        "jp": "接続元",
    },
    "device_dialog.link_search": {
        "vi": "Tìm thiết bị kết nối...",
        "en": "Search linked devices...",
        "jp": "リンクデバイスを検索...",
    },
    "device_kind.camera": {
        "vi": "Camera",
        "en": "Camera",
        "jp": "カメラ",
    },
    "device_kind.server": {
        "vi": "Server",
        "en": "Server",
        "jp": "サーバー",
    },
    "device_kind.switch": {
        "vi": "Switch",
        "en": "Switch",
        "jp": "スイッチ",
    },
    "device_kind.hub": {
        "vi": "Hub",
        "en": "Hub",
        "jp": "ハブ",
    },
    "device_kind.dvr": {
        "vi": "DVR",
        "en": "DVR",
        "jp": "DVR",
    },
    "device_kind.ap": {
        "vi": "AP",
        "en": "AP",
        "jp": "AP",
    },
    "device_kind.router": {
        "vi": "Router",
        "en": "Router",
        "jp": "ルーター",
    },
    "device_kind.firewall": {
        "vi": "Firewall",
        "en": "Firewall",
        "jp": "ファイアウォール",
    },
    "device_kind.pc": {
        "vi": "PC",
        "en": "PC",
        "jp": "PC",
    },
    "device_variant.fixed": {
        "vi": "Cố định",
        "en": "Fixed",
        "jp": "固定",
    },
    "device_variant.ptz": {
        "vi": "PTZ",
        "en": "PTZ",
        "jp": "PTZ",
    },
    "device_variant.dome": {
        "vi": "Dome",
        "en": "Dome",
        "jp": "ドーム",
    },
    "device_variant.fisheye": {
        "vi": "Fisheye",
        "en": "Fisheye",
        "jp": "魚眼",
    },
    "device_variant.360": {
        "vi": "360 độ",
        "en": "360-degree",
        "jp": "360度",
    },
    "device_variant.ai": {
        "vi": "AI",
        "en": "AI",
        "jp": "AI",
    },
    "device_variant.rack": {
        "vi": "Rack",
        "en": "Rack",
        "jp": "ラック",
    },
    "device_variant.tower": {
        "vi": "Tower",
        "en": "Tower",
        "jp": "タワー",
    },
    "device_variant.nas": {
        "vi": "NAS",
        "en": "NAS",
        "jp": "NAS",
    },
    "device_variant.nvr": {
        "vi": "NVR",
        "en": "NVR",
        "jp": "NVR",
    },
    "device_variant.workstation": {
        "vi": "Workstation",
        "en": "Workstation",
        "jp": "ワークステーション",
    },
    "device_variant.pc": {
        "vi": "PC",
        "en": "PC",
        "jp": "PC",
    },
    "device_variant.laptop": {
        "vi": "Laptop",
        "en": "Laptop",
        "jp": "ノートPC",
    },
    "device_variant.core": {
        "vi": "Core",
        "en": "Core",
        "jp": "コア",
    },
    "device_variant.distribution": {
        "vi": "Distribution",
        "en": "Distribution",
        "jp": "ディストリビューション",
    },
    "device_variant.access": {
        "vi": "Access",
        "en": "Access",
        "jp": "アクセス",
    },
    "device_variant.poe": {
        "vi": "PoE",
        "en": "PoE",
        "jp": "PoE",
    },
    "device_variant.managed": {
        "vi": "Managed",
        "en": "Managed",
        "jp": "管理型",
    },
    "device_variant.unmanaged": {
        "vi": "Unmanaged",
        "en": "Unmanaged",
        "jp": "非管理型",
    },
    "device_variant.ethernet_hub": {
        "vi": "Ethernet Hub",
        "en": "Ethernet Hub",
        "jp": "Ethernet Hub",
    },
    "device_variant.usb_hub": {
        "vi": "USB Hub",
        "en": "USB Hub",
        "jp": "USB Hub",
    },
    "device_variant.patch_hub": {
        "vi": "Patch Hub",
        "en": "Patch Hub",
        "jp": "Patch Hub",
    },
    "device_variant.dvr": {
        "vi": "DVR",
        "en": "DVR",
        "jp": "DVR",
    },
    "device_variant.hybrid_dvr": {
        "vi": "Hybrid DVR",
        "en": "Hybrid DVR",
        "jp": "Hybrid DVR",
    },
    "device_variant.indoor_ap": {
        "vi": "Indoor AP",
        "en": "Indoor AP",
        "jp": "Indoor AP",
    },
    "device_variant.outdoor_ap": {
        "vi": "Outdoor AP",
        "en": "Outdoor AP",
        "jp": "Outdoor AP",
    },
    "device_variant.ceiling_ap": {
        "vi": "Ceiling AP",
        "en": "Ceiling AP",
        "jp": "Ceiling AP",
    },
    "device_variant.mesh_ap": {
        "vi": "Mesh AP",
        "en": "Mesh AP",
        "jp": "Mesh AP",
    },
    "device_variant.edge_router": {
        "vi": "Edge Router",
        "en": "Edge Router",
        "jp": "Edge Router",
    },
    "device_variant.wifi_router": {
        "vi": "WiFi Router",
        "en": "WiFi Router",
        "jp": "WiFi Router",
    },
    "device_variant.vpn_router": {
        "vi": "VPN Router",
        "en": "VPN Router",
        "jp": "VPN Router",
    },
    "device_variant.utm": {
        "vi": "UTM",
        "en": "UTM",
        "jp": "UTM",
    },
    "device_variant.ngfw": {
        "vi": "NGFW",
        "en": "NGFW",
        "jp": "NGFW",
    },
    "device_variant.hardware_firewall": {
        "vi": "Hardware Firewall",
        "en": "Hardware Firewall",
        "jp": "Hardware Firewall",
    },
    "device_variant.virtual_firewall": {
        "vi": "Virtual Firewall",
        "en": "Virtual Firewall",
        "jp": "Virtual Firewall",
    },
    "status.device_updated": {
        "vi": "Đã cập nhật thiết bị '{name}'.",
        "en": "Updated device '{name}'.",
        "jp": "デバイス「{name}」を更新しました。",
    },
    "status.device_link_created": {
        "vi": "Đã tạo liên kết thiết bị.",
        "en": "Created device link.",
        "jp": "デバイスリンクを作成しました。",
    },
    "status.device_link_skipped": {
        "vi": "Không thể tạo liên kết thiết bị.",
        "en": "Could not create device link.",
        "jp": "デバイスリンクを作成できませんでした。",
    },
    "status.device_link_removed": {
        "vi": "Đã gỡ kết nối thiết bị.",
        "en": "Removed device link.",
        "jp": "デバイスリンクを削除しました。",
    },
    "status.device_link_remove_failed": {
        "vi": "Không thể gỡ kết nối thiết bị.",
        "en": "Could not remove device link.",
        "jp": "デバイスリンクを削除できませんでした。",
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
