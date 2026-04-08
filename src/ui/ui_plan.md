# Kế hoạch Triển khai UI/UX Đăng nhập qua Clerk (V2 - Cập nhật)

Bản kế hoạch này tích hợp xác thực sử dụng **Clerk** cho ứng dụng AI Tutor, kết hợp yêu cầu mới: Sử dụng Google SSO, hỗ trợ Light/Dark Mode và dùng UI Component có sẵn của Clerk.

## Các quyết định thiết kế đã chốt:
1. **Giao diện & Thành phần**: Sử dụng UI có sẵn của Clerk (tối ưu tính bảo mật và trải nghiệm).
2. **Phương thức Đăng nhập**: Dùng Google (Nhập email hoặc click "Tiếp tục với Google"). Clerk có sẵn tuỳ chọn kết nối Google SSO.
3. **Trải nghiệm Light/Dark mode**: Có nút chuyển đổi linh hoạt. Giao diện nền ứng dụng và bản thân cái Form của Clerk cũng sẽ tự động đổi màu tương ứng khi người dùng bật/tắt công tắc này.

## Luồng Hoạt động (Authentication Flow)

1. **Trạng thái Chưa đăng nhập**: 
   - Truy cập vào `/index.html` → Script của Clerk kiểm tra → Chưa đăng nhập → Tự động đẩy sang `/login.html`.
2. **Tại `/login.html`**:
   - Giao diện tối giản. Ở giữa là Form đăng nhập của Clerk, trên góc có nút chuyển Light/Dark Mode.
   - Khi đổi Light/Dark mode ở ngoài, màu nền Form Clerk cũng đổi theo (Bằng cách update thuộc tính `appearance.baseTheme`).
3. **Trạng thái Đã đăng nhập**:
   - Click đăng nhập Google thành công → Quay trở lại `/index.html`.
   - Trên Header sẽ xuất hiện Avatar người dùng của Clerk (thay vì nút Hỏi Gia Sư mặc định), cùng với công tắc Light/Dark Mode.

## Proposed Changes

---

### Thiết lập Hệ thống Màu (Light/Dark Variables)

#### [MODIFY] [index.html](file:///d:/VSCODE/VINAI/A20-App-049/src/api/static/index.html)
- **CSS Theme**: Thêm thuộc tính `[data-theme='light']` trong CSS, thay đổi các giá trị `--bg`, `--card`, `--text` thành các tông màu trắng xám.
- **Header Element**: Thêm nút Switch "☀️ / 🌙" nằm ở góc phải Header, nằm ngay cạnh vị trí chuẩn bị xuất hiện của User Avatar Clerk (`<div id="user-button"></div>`).
- **Logic Theme**: Dùng JavaScript để lưu tùy chọn Theme vào `localStorage`, đảm bảo nếu F5 web vẫn giữ nguyên chế độ sáng tối tương ứng.
- **Clerk Integration**: Thêm code Script `<script>` khởi tạo và kiểm tra `window.Clerk.user`. Nếu hợp lệ thì hiển thị Account Avatar.

#### [NEW] [login.html](file:///d:/VSCODE/VINAI/A20-App-049/src/api/static/login.html)
- Tái sử dụng hệ thống CSS `[data-theme='light']`.
- **UI Element**: Gồm nút Switch ở góc, và một thẻ div container căn giữa màn hình cho nội dung Clerk. 
- **Clerk SignIn Rendering**:
   ```javascript
   function renderClerkForm() {
       const isDark = document.body.getAttribute('data-theme') !== 'light';
       Clerk.mountSignIn(document.getElementById('sign-in'), {
           appearance: {
               // Dùng baseTheme dark nếu ở chế độ tối
               baseTheme: isDark ? window.Clerk.dark : undefined,
               variables: { colorPrimary: '#38bdf8' }
           }
       });
   }
   ```
   Mỗi khi gạt nút thả Mode, ta gỡ (`unmountSignIn`) form hiện tại và mount (`mountSignIn`) form mới với theme tương ứng để thay đổi lập tức trơn tru.

---

## Open Questions

- **Khởi tạo Clerk.js**: App hiện tại không có bundler NPM cho Frontend (chỉ dùng CDN/Vanilla js). Do đó để lấy file theme dark (`window.Clerk.dark`), ta có thể cần kéo CDN thư viện `@clerk/themes` hoặc viết custom color.
- **Cấu hình Clerk Dashboard**: Tính năng Đăng nhập qua Google (SSO) này yêu cầu bạn phải được [Bật Google Social Login] trên phần "User & Authentication > Social Connections" trong tài khoản Dashboard của Clerk. Bạn nhớ kiểm tra kỹ phần này nhé!

## Verification Plan

### Test kịch bản:
- Truy cập thẳng trang bài giảng `index.html` → Kiểm tra Auth Guard chặn và đẩy về `/login.html` thành công.
- Trên trang `/login.html`: Bấm nút Switch Mode sáng tối → Background tối lại và Form Sign In của Clerk cũng tự động tối theo.
- Đăng nhập thử với tài khoản Google. Xác nhận sau khi đăng nhập xong tự trả về màn hình khóa học bài giảng (`/index.html`).
- Kiểm tra Avatar user ở góc màn hình. Bấm vào Avatar -> Nổi lên popup Account Management từ Clerk chuẩn xác.
