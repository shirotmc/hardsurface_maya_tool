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
- **Speed Tool:** Edge Length, Straighten, Average, ShrinkWrap, Unbevel, Snap, Cable, Decal, Clear spEdge, Swap LOD, Rename, Screenshot, Material.
- **Fast Function:** Split Polygon, Extend Face, Fill Face, Match Scale, Reset Object.
- **Fix Maya**, **Maya - Blender** và **Import/Export:** tiện ích sửa lỗi Maya và trao đổi file với Blender.

### Slide Snap (Model tab, Speed Tool, nút **Snap**)
Snap các vertex đang chọn lên mặt phẳng của một face bằng cách trượt dọc một đường.
1. **Pick Face** để chọn face đích, rồi chọn các vertex cần snap.
2. **Slide Direction:** Along Edge (dọc cạnh của vertex), X, Y, Z hoặc Normal (thẳng góc vào face).
3. **Snap Vertices**. Vertex không snap được (cạnh song song với mặt, quá xa...) được chọn lại kèm thông báo lý do.

### Material Manager (Model tab, Speed Tool, nút **Material**)
Cửa sổ riêng để quản lý material, giao diện cùng phong cách với HSTool. Tab **Scene**, **Color Presets** và **ID Map Baker**.
- **Material List:** tên material (xanh = đang gán cho vùng chọn), ô màu để **gán** vào vùng chọn, ô đánh dấu để chọn nhiều material.
  Click chọn, Shift chọn dải, Alt bật/tắt, Ctrl chọn các object/face đang dùng material đó.
- **Create / Edit:** tạo nhanh Lambert, Phong, Blinn, Standard Surface (Ctrl: thêm vào scene, không hỏi tên), nhân bản, Match, đổi tên, xóa.
  Đổi tên hoặc nhân bản sẽ đổi tên luôn shading group, file và place2d theo material.
- **Texture Channels:** thêm map Color, Normal, Roughness, Metallic, Specular, Occlusion, Emissive, Opacity cho material;
  ô xanh báo kênh đang có map, bấm để xóa. **Load Textures From Folder** tự tìm và nối map theo hậu tố tên file (chỉnh ở **Suffixes**).
- **Color Presets:** 15 màu ID và hơn 50 material mẫu (Brick, Metal_Steel...). Chế độ *Assign to Selection* hoặc *Add to Scene*.
- **ID Map Baker:** gán màu ID tự động (theo element hoặc object), chọn high / low / cage, rồi bake bản đồ màu ID.
- **Tools:** UV Border (hard edge theo UV shell), đổi handedness, colorize, material thành vertex color, xóa namespace, tự đặt tên material theo object.
- **Cleanup:** xóa material không dùng, xóa node thừa, đổi tên đồng bộ, thêm tiền tố `M_`, purge scene.

Dữ liệu preset nằm ở `Material_Tools/Data/mm_material_presets.txt` (một dòng một material, sửa được).
Material Manager dựa trên bản gốc của Dennis Porter, xem phần Giấy phép bên dưới.

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

## Giấy phép

Phần **Material Manager** (`Material_Tools/`) là bản viết lại bằng Python của
[Material Manager v5.2.0](https://github.com/Bartalon/Material-Manager) của Dennis Porter, phát hành theo **GNU GPL v3**.
Do đó phần này (và bản phân phối chứa nó) cũng theo GPL v3. Xem file `LICENSE` và `Material_Tools/NOTICE.md`.
Các phần còn lại của HSTool không bị ảnh hưởng nếu được tách riêng, nhưng bản phân phối gộp phải tuân thủ GPL v3.

## Liên hệ

Canh Tran (shiro.tmc@gmail.com)
