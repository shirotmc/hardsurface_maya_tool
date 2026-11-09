# HSTool - Hard Surface Toolset for Maya

Bộ công cụ Maya cho modeling hard surface: kiểm tra scene, modeling, mirror, normal, UV và bake.
Hỗ trợ Maya 2018 – 2025 (Python 2 và 3). Có cập nhật online qua GitHub Releases.

## Cài đặt

1. Tải `HSTool.zip` từ trang [Releases](https://github.com/shirotmc/hardsurface_maya_tool/releases/latest) và giải nén vào một thư mục cố định, ví dụ `D:\Tools\HSTool`.
   Đừng đặt trong thư mục tạm, và giữ nguyên tên folder cùng cấu trúc bên trong.
2. Mở Maya, kéo file `install.py` trong folder vừa giải nén thả vào viewport.
3. Menu **HardSurface_Tools** xuất hiện trên thanh menu chính, chọn **HardSurface Toolset** để mở tool.

Installer ghi file `Documents/maya/modules/HSTool.mod` trỏ tới folder của bạn, nên các lần mở Maya sau menu tự có sẵn.

Có thể chạy trực tiếp từ Script Editor (Python):

```python
from HardSurface_Tool import HardSurfaceTool
HardSurfaceTool.GUI()
```

(chỉ chạy được khi gốc HSTool đã nằm trong `sys.path`, cách cài bằng `install.py` ở trên đã lo việc này).

## Cập nhật

Menu **Update** của tool có hai mục: **Update Tool** và **Check For Updates**.

- Khi mở tool, updater tự kiểm tra ngầm (mặc định 12 giờ một lần) và không làm đơ Maya.
- Có bản mới thì hiện hộp thoại kèm release notes. Bấm **Update** để tải về, kiểm tra SHA256 rồi cập nhật.
- File cũ được backup vào `HSTool_backup/` (cạnh folder HSTool, giữ 3 bản gần nhất). Lỗi giữa chừng sẽ tự khôi phục.
- Settings của bạn (`HardSurfaceTool_Setting.json`) được giữ nguyên.
- Sau khi cập nhật, đóng tool và mở lại, nên khởi động lại Maya cho chắc.

Cấu hình trong `Updater/update_config.json`:

| Khoá | Ý nghĩa |
|---|---|
| `repo` | Repo GitHub, dạng `owner/name` |
| `asset_name` | Tên file zip trong Release (`HSTool.zip`) |
| `token_env` | Tên biến môi trường chứa token (chỉ cần cho repo private) |
| `check_interval_hours` | Số giờ giữa hai lần tự kiểm tra |
| `auto_check_on_startup` | `false` để tắt tự kiểm tra |
| `preserve` | Danh sách file không bị ghi đè khi update |

Repo private: đặt token chỉ đọc vào biến môi trường rồi khởi động lại Maya.

```
setx HSTOOL_GITHUB_TOKEN "ghp_xxx"
```

## Các tab chức năng

### Check
Quét lỗi scene, mỗi dòng có nút **Check** và (nếu có) nút **Fix**. **Check All** chạy toàn bộ.
Ô trên cùng hiển thị thời điểm mở và thời điểm kiểm tra gần nhất. Nút đổi màu đỏ khi có lỗi và xanh khi sạch.

- **Check Scene:** World Coordinate System, Scene Unit, Delete History, Freeze Transform, Default Cameras, Empty Group, Instance Object.
- **Check Modeling:** Color Set, Face More Than Four, Concave Face, Nonmanifold/Lamina Edges, Zero Area Face, Unweld Vertex.
- **Check UV:** Tiny UV, Zero UV, **UV Overlap** (face có UV chồng nhau), **UV Flip** (face bị lật UV).
- **Check Shader:** Unused Node.
- **Check Maya:** scriptNode lạ trong scene, file/thư mục đáng ngờ trong thư mục scripts của Maya.
- **Clean UP:** tắt Double Side, scan scene, optimize scene, dọn attribute thừa, xóa namespace.

Hầu hết check chọn luôn các đối tượng lỗi trong scene để bạn xử lý. Các check UV chỉ kiểm tra đối tượng đang chọn.

### Model
- **Circle:** căn đỉnh thành hình tròn (Diameter/Angle tuỳ chọn, Get Priority, Contiguous, Ring).
- **Select:** Dot Loop / Dot Ring, chọn theo góc co-planar, Select Similar Object, Selection Set.
- **Modify Object:** Combine, Detach, Clone, Detach By Mat, Center/Reset/Set/Object Pivot.
- **Scene:** Unhide All, Freeze Transforms, Y/Z, FCC (Force Clean Combine), History, Silhouette.
- **Instance:** Set Instance, Un-Instance.
- **Speed Tool:** Edge Length, Straighten, Average, ShrinkWrap, Unbevel, Snap, Cable, Decal, Clear spEdge, Swap LOD, Rename, Screenshot.
- **Fast Function:** Split Polygon, Extend Face, Fill Face, Match Scale, Reset Object.
- **Fix Maya**, **Maya - Blender** và **Import/Export:** tiện ích sửa lỗi Maya và trao đổi file với Blender.

### Mirror
- **FLIP / MIRROR / INSTANCE** theo X, Y, Z.
- **MERGE:** mirror và merge theo +X/+Y/+Z/-X/-Y/-Z.
- **CUT:** Mirror Cut.
- **REVOLVE:** Revolve X/Y/Z, có tuỳ chọn Instance.

### Normal
- **Display Vertex Normal:** bật/tắt hiển thị normal (vùng chọn hoặc toàn bộ).
- **Copy/Paste Normal:** copy, paste, lấy trung bình, target weld giữ normal, collapse edge giữ normal, đảo normal.
- **Lock Normal:** Lock/Unlock, giữ Hard/Soft, chuyển normal đã khoá thành Hard/Soft Edge, lock theo mặt nhỏ hoặc lớn, smooth bevel, lock face theo góc 90.
- **Transfer Normal:** chọn Source rồi chuyển sang mesh hoặc vertex.
- **Connect Normal:** nối normal giữa các phần, có hoặc không theo flow.

### UV
- **Unwrap:** UW Select Edge, UW Hard Edge, Hard Edge, Open Edge, Set UV Border.
- **Layout:** UV Grid, Unfold, Transfer UV, Match UV, Scale, Group Scale, UV To PTS.
- **RizomUV:** Open RizomUV, chọn bản exe, Export To Rizom, Import To Maya.
- **UV Checker:** áp texture checker (15 mẫu) lên đối tượng.
- **UV Set:** Set Default UVSet, Sort UVSet List, Rename, Copy, Delete, Editor.

### Bake
- **Normal Map / AO Map:** chọn file map, áp lên đối tượng hoặc xoá.
- **Tangent Space:** Right Handed hoặc Left Handed.
- **Setup Bake Scene:** Rename Highpoly, Create BakeSet (chọn High và Low), Auto Create BakeSet, Create HighLow Layer, Expand/Collapse All Group.
- **Export FBX:** Export Selected BakeSet hoặc Export All BakeSet.

## Hotkey

Menu **Hotkey** có hai mục:
- **Get Hotkey Command:** nạp bộ lệnh hotkey của tool vào Maya (`userRunTimeCommands.mel` và `userNamedCommands.mel`).
- **Open Hotkey Editor:** mở Hotkey Editor để gán phím cho các lệnh đó.

## Giao diện

Menu **UI** cho phép đổi màu Frame, màu Button, hoặc Reset Color. Cài đặt lưu trong `HardSurface_Tool/Database/Setting/HardSurfaceTool_Setting.json`.

## Cấu trúc thư mục

```
HSTool/
  install.py              Cài đặt kéo-thả
  version.json            Phiên bản hiện tại
  plug-ins/               Plug-in tạo menu HardSurface_Tools
  Updater/                Updater online + build_release.py
  HardSurface_Tool/       Cửa sổ chính, Database (setting, hotkey, library, document)
  Check_Tools/ Model_Tools/ Mirror_Tools/ Normal_Tools/ UV_Tools/ BakeSet_Tools/
```

## Liên hệ

Canh Tran (shiro.tmc@gmail.com)
