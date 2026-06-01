# 🛠️ Project-Specific AI Agent Standards

This file contains standards, conventions, and rules specific to this project. AI Agents MUST adhere to the rules herein, in parallel with the core standards (like `GEMINI.md`, `CLAUDE.md`).

> **💡 Instructions:**
> - **Independent operation:** Simply create/edit this file, and the AI Agent will automatically detect it.
> - **Fully customizable:** You can add new fields (e.g., "Reviewer", "Effective Date") if necessary. Just keep it in a bulleted list format.
> - Use this file to define: project architecture, preferred libraries, naming conventions, error handling flows, etc.

---

## 🏗️ Template

*(Copy the block below to add a new standard. You can add/remove any fields according to your needs)*

### [Standard Name / Category]
- **Rule (Required):** [Clear description of the rule the AI must follow]
- **Reason (Required):** [Brief explanation of why this rule exists]
- **Do / Good Example (Optional):** [Example of correct code/behavior]
- **Don't / Bad Example (Optional):** [Example of incorrect code/behavior]
- **Scope (Optional):** [e.g.: Only applies to Frontend code, or only .ts files]
- **Reference (Optional):** [Link or path to documentation, design file, issue...]
- **Exceptions (Optional):** [Cases where this rule does not apply]
- **Terminal Command (Optional):** [Commands to run, e.g.: npm run lint]
- **How to Test (Optional):** [How to know this rule has been followed?]

---

## 📋 Project Standards List (Customize below)

*(You can check the `PROJECT-STANDARDS-EXAMPLE.md` file in the same directory for available template examples and copy/paste them here to enforce them as hard rules for your project)*

Dưới đây là các **Standard** được trích xuất từ hướng dẫn chi tiết cho AI Agent, trình bày theo mẫu yêu cầu:

---

### 1. File Size & Single Responsibility
- **Rule (Required):** Mỗi file code không được vượt quá 300 dòng (đã trừ comment và blank line). Mỗi file chỉ đảm nhận DUY NHẤT một trách nhiệm (Single Responsibility Principle).
- **Reason (Required):** Đảm bảo dễ đọc, dễ bảo trì, giảm xung đột Git, tăng khả năng tái sử dụng và test độc lập. File quá lớn (>300 dòng) thường chứa nhiều trách nhiệm khác nhau, gây khó hiểu và dễ sinh lỗi khi sửa.
- **Do / Good Example (Optional):**
  ```python
  # user_service.py (150 dòng) - Chỉ CRUD user
  class UserService:
      def create_user(self, data): ...
      def get_user(self, user_id): ...
      def update_user(self, user_id, data): ...
      def delete_user(self, user_id): ...
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # user_manager.py (850 dòng) - Làm 7 việc khác nhau
  class UserManager:
      def create_user(self): ...      # CRUD
      def send_email(self): ...       # Notification
      def log_activity(self): ...     # Logging
      def validate_data(self): ...    # Validation
      def calculate_tax(self): ...    # Tax logic (??)
      def generate_report(self): ...  # Reporting
      def backup_db(self): ...        # Database backup
  ```
- **Scope (Optional):** Toàn bộ codebase trừ các file cấu hình (config, constants, env) và file sinh tự động (code generation).
- **Reference (Optional):** Single Responsibility Principle - Robert C. Martin (Clean Code, Chapter 3)
- **Exceptions (Optional):**
  - File cấu hình (config.py, constants.ts, .env) có thể >300 dòng vì ít thay đổi và chỉ đọc một lần khi start app.
  - File chứa thuật toán phức tạp, logic liền mạch (flow liên tục) có thể lên tới 500 dòng nếu tách ra sẽ phá vỡ tính liên tục.
  - File sinh tự động từ code generator hoặc DSL nội bộ.
- **Terminal Command (Optional):**
  ```bash
  # Đếm số dòng thực tế (bỏ qua comment và blank line)
  find src -name "*.py" -exec sh -c 'echo "$(grep -cve "^\s*#" -e "^$" "$1") $1"' _ {} \; | awk '$1 > 300'
  ```
- **How to Test (Optional):**
  - Chạy script đếm dòng tự động trong CI/CD pipeline.
  - Nếu có file >300 dòng (không thuộc exception), pipeline báo lỗi.
  - Code review bắt buộc kiểm tra trách nhiệm duy nhất của mỗi file.

---

### 2. No Circular Dependency Before Refactoring
- **Rule (Required):** TRƯỚC KHI tách file lớn thành nhiều file nhỏ, AI Agent PHẢI kiểm tra và đảm bảo KHÔNG tạo ra dependency vòng tròn (circular import / cyclic dependency). Nếu phát hiện, phải dừng refactor và báo cáo.
- **Reason (Required):** Circular dependency gây lỗi runtime (ImportError), làm code khó test, khó hiểu, và khiến việc tách file phản tác dụng. Một khi đã có circular dependency, việc bảo trì trở nên rất khó khăn.
- **Do / Good Example (Optional):**
  ```python
  # ĐÚNG: Dependency Injection qua interface
  class A:
      def do(self, logger: ILogger): ...  # Inject dependency, không import trực tiếp
  
  class B:
      def log(self, msg): ...
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Circular dependency
  # a.py
  from b import B
  class A:
      def use_b(self): return B()
  
  # b.py
  from a import A  # ← Vòng tròn: a -> b -> a
  class B:
      def use_a(self): return A()
  ```
- **Scope (Optional):** Áp dụng cho tất cả ngôn ngữ có hệ thống import module (Python, JavaScript/TypeScript, Java, Go, C#).
- **Reference (Optional):** https://en.wikipedia.org/wiki/Circular_dependency
- **Exceptions (Optional):** KHÔNG có ngoại lệ. Circular dependency luôn là lỗi kiến trúc cần sửa trước khi refactor.
- **Terminal Command (Optional):**
  ```bash
  # Python
  pip install pylint
  pylint --errors-only --disable=all --enable=import-error,R0401 old_file.py
  
  # TypeScript/JavaScript
  npx madge --circular --extensions ts src/
  
  # General
  pip install pipdeptree
  pipdeptree --reverse --packages <package_name>
  ```
- **How to Test (Optional):**
  - Chạy lệnh kiểm tra circular dependency trong CI/CD.
  - Nếu phát hiện circular, pipeline fail và không cho phép merge.
  - Code review bắt buộc kiểm tra sơ đồ dependency trước khi approve.

---

### 3. Preserve Public API & Behavior
- **Rule (Required):** Khi tách file lớn thành các file nhỏ, KHÔNG được thay đổi behavior (hành vi) của code và KHÔNG được thay đổi public API trừ khi bất khả kháng. Tất cả các test hiện tại vẫn phải chạy xanh (pass).
- **Reason (Required):** Refactor an toàn là refactor không làm thay đổi chức năng bên ngoài. Thay đổi API hoặc behavior sẽ phá vỡ các module phụ thuộc, gây lỗi production và mất niềm tin vào quá trình refactor.
- **Do / Good Example (Optional):**
  ```python
  # TRƯỚC: File cũ có function
  def process_order(order_id):
      # 500 dòng logic
      return result
  
  # SAU: Giữ nguyên function signature, chuyển logic sang module mới
  from order_processor import OrderProcessor
  def process_order(order_id):
      processor = OrderProcessor()
      return processor.process(order_id)  # Behavior giống hệt
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Thay đổi API
  # TRƯỚC: process_order(order_id) -> returns dict
  # SAU: process_order(order_id, user_context) -> returns CustomObject  # Phá vỡ caller
  ```
- **Scope (Optional):** Toàn bộ codebase, đặc biệt là các module được export/share giữa nhiều file/project.
- **Reference (Optional):** "Refactoring: Improving the Design of Existing Code" - Martin Fowler (Chapter 2: Principles in Refactoring)
- **Exceptions (Optional):**
  - Chỉ thay đổi API nếu đã có kế hoạch migration với deprecation warning ít nhất 2 version.
  - Code internal (private method) có thể thay đổi nếu không ảnh hưởng module khác.
- **Terminal Command (Optional):**
  ```bash
  # Chạy toàn bộ test suite trước và sau refactor
  pytest tests/ --cov=src/ --cov-report=term
  
  # So sánh kết quả test
  pytest tests/ --tb=short --maxfail=1
  ```
- **How to Test (Optional):**
  - Chạy lại toàn bộ test suite (unit test, integration test, regression test).
  - Coverage không được giảm quá 2% so với trước refactor.
  - Chạy smoke test trên môi trường staging trước khi merge.

---

### 4. Cyclomatic Complexity per File
- **Rule (Required):** Mỗi file sau refactor phải có cyclomatic complexity < 15. Nếu vượt quá, phải tiếp tục tách hoặc đơn giản hóa logic.
- **Reason (Required):** Cyclomatic complexity đo số lượng đường đi độc lập qua code. Complexity càng cao, code càng khó hiểu, khó test và dễ có lỗi tiềm ẩn. Giới hạn <15 đảm bảo mỗi file có thể được hiểu bởi một developer trung bình trong vòng 5-10 phút.
- **Do / Good Example (Optional):**
  ```python
  # ĐÚNG: Complexity ~8
  def calculate_price(base_price, user_type, coupon):
      price = base_price
      if user_type == "vip":
          price *= 0.9
      if coupon and coupon.is_valid():
          price -= coupon.value
      return max(0, price)
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Complexity ~35 (quá nhiều if-else lồng nhau)
  def process(data):
      if data.get("type") == "A":
          if data.get("status") == "active":
              if data.get("flag"):
                  for item in data.get("items", []):
                      if item["price"] > 100:
                          if item["category"] in ["x", "y", "z"]:
                              # ... còn 5 tầng if nữa
                              pass
  ```
- **Scope (Optional):** Tất cả file code logic (trừ file cấu hình, file data mapping đơn giản).
- **Reference (Optional):** Thomas J. McCabe (1976) - "A Complexity Measure"
- **Exceptions (Optional):**
  - File switch-case với 15+ case (state machine) có thể chấp nhận complexity cao hơn.
  - File parser/serializer theo chuẩn bắt buộc.
- **Terminal Command (Optional):**
  ```bash
  # Python
  pip install radon
  radon cc src/ --min C --show-complexity
  
  # JavaScript/TypeScript
  npx eslint --rule 'complexity: ["error", 15]' src/
  ```
- **How to Test (Optional):**
  - Tự động chạy linter với rule complexity trong CI.
  - Nếu complexity >15, pipeline fail và yêu cầu refactor tiếp.

---

### 5. Documentation & Type Hints in Every File
- **Rule (Required):** Mỗi file mới được tạo ra PHẢI có:
  - Docstring/module-level comment mô tả trách nhiệm duy nhất của file.
  - Type hint đầy đủ cho tất cả function parameters và return values (nếu ngôn ngữ hỗ trợ).
- **Reason (Required):** Documentation giúp developer (và AI Agent khác) hiểu ngay mục đích của file mà không cần đọc toàn bộ code. Type hint giảm thiểu lỗi runtime, cải thiện autocomplete và làm code tự documenting.
- **Do / Good Example (Optional):**
  ```python
  """
  Module: tax_calculator.py
  Trách nhiệm: Tính thuế cho đơn hàng dựa trên vị trí địa lý và loại sản phẩm.
  Chỉ xử lý logic thuế, không liên quan đến giỏ hàng hay thanh toán.
  """
  from typing import Optional
  
  def calculate_tax(amount: float, location: str, product_type: str) -> float:
      """Tính thuế VAT hoặc GST tùy theo location."""
      ...
  
  def get_tax_rate(location: str, product_type: str) -> Optional[float]:
      """Lấy税率 dựa trên location. Trả về None nếu không áp dụng thuế."""
      ...
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Không có docstring, không type hint
  # tax.py
  def calc(x, y, z):
      # ai hiểu cái này làm gì?
      if y == "VN":
          return x * 0.1
      return x * 0.05 if z == "elec" else x * 0.08
  ```
- **Scope (Optional):** 
  - Python: type hints bắt buộc từ Python 3.6+, dùng `from typing import ...`
  - TypeScript: explicit typing, tránh `any`
  - Java/C#: type đã có sẵn, cần comment XML/JavaDoc cho public method
- **Reference (Optional):** 
  - PEP 8 – Docstring conventions
  - PEP 484 – Type Hints
  - Google Python Style Guide
- **Exceptions (Optional):**
  - File rất nhỏ (<30 dòng) và rõ ràng (ví dụ: constants.py với 10 hằng số) có thể bỏ qua docstring.
  - Test file (test_*.py) có thể bỏ qua docstring nếu tên test method đã self-documenting.
- **Terminal Command (Optional):**
  ```bash
  # Kiểm tra Python docstring
  pip install pydocstyle
  pydocstyle src/
  
  # Kiểm tra type hint (Python)
  pip install mypy
  mypy src/ --strict
  
  # TypeScript
  npx tsc --noEmit --strict
  ```
- **How to Test (Optional):**
  - Chạy linter với rule docstring và type hint trong pre-commit hook.
  - CI pipeline fail nếu thiếu docstring hoặc type hint không đúng.

---

### 6. Branch by Abstraction for Safe Refactoring
- **Rule (Required):** Khi tách file lớn (>500 dòng) có nhiều module phụ thuộc, PHẢI áp dụng chiến lược "Branch by Abstraction": giữ lại proxy layer trong file cũ, chuyển dần các caller sang module mới, sau 1-2 tuần (khi không còn lỗi) mới xóa file cũ.
- **Reason (Required):** Thay đổi đột ngột (big bang refactor) dễ gây lỗi lan rộng, ảnh hưởng production. Branch by Abstraction cho phép thay đổi từ từ, rollback dễ dàng nếu có vấn đề, và đảm bảo zero downtime.
- **Do / Good Example (Optional):**
  ```python
  # BƯỚC 1: Giữ file cũ làm proxy
  # old_file.py
  from new_module import NewProcessor
  
  class OldProcessor:
      def __init__(self):
          self._new = NewProcessor()
      
      def process(self, data):
          # Forward to new module, behavior không đổi
          return self._new.process(data)
  
  # BƯỚC 2: Từ từ update caller (tuần 1)
  # caller.py
  # from old_file import OldProcessor  ← Cách cũ
  from new_module import NewProcessor   # Cách mới
  
  # BƯỚC 3: Sau 2 tuần, xóa old_file.py
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Xóa file cũ ngay lập tức
  # old_file.py (đã xóa)
  # caller.py bỗng nhiên bị lỗi import vì đang dùng OldProcessor
  ```
- **Scope (Optional):** Áp dụng cho file >500 dòng hoặc file có >5 module phụ thuộc trực tiếp.
- **Reference (Optional):** Martin Fowler - "BranchByAbstraction" (https://martinfowler.com/bliki/BranchByAbstraction.html)
- **Exceptions (Optional):**
  - File <300 dòng và chỉ có 1-2 caller → có thể thay đổi trực tiếp.
  - Personal project / prototype → không cần strict.
- **Terminal Command (Optional):**
  ```bash
  # Tìm tất cả file import vào module cũ
  grep -r "from old_file import" --include="*.py" src/
  
  # Theo dõi số lượng caller còn dùng proxy
  grep -r "OldProcessor" --include="*.py" src/ | wc -l
  ```
- **How to Test (Optional):**
  - Trong tuần đầu, cả hai cách (caller dùng proxy và caller dùng trực tiếp module mới) đều phải pass test.
  - Monitoring lỗi import trong production sau mỗi lần deploy incremental.

---

### 7. No Arbitrary Refactoring Based on Line Count Alone
- **Rule (Required):** KHÔNG được tách file chỉ vì nó >300 dòng mà không phân tích trách nhiệm. Phải chứng minh file đang làm nhiều hơn 3 trách nhiệm khác nhau trước khi quyết định tách.
- **Reason (Required):** Tách máy móc dựa trên số dòng có thể tạo ra nhiều file nhỏ nhưng dependency phức tạp hơn, maintain khó hơn file gốc. Mục tiêu cuối cùng là code dễ hiểu, không phải số dòng thấp bằng mọi giá.
- **Do / Good Example (Optional):**
  ```python
  # PHÂN TÍCH TRƯỚC KHI TÁCH
  # File: payment_gateway.py (400 dòng)
  # Trách nhiệm phát hiện:
  # 1. Kết nối Stripe API (80 dòng)
  # 2. Xử lý webhook (90 dòng)
  # 3. Logging payment (70 dòng)
  # 4. Validate card (60 dòng)
  # 5. Calculate fee (50 dòng)
  # 6. Retry logic (50 dòng)
  # → 6 trách nhiệm → CẦN TÁCH
  
  # File: matrix_multiply.py (380 dòng)
  # Trách nhiệm: Chỉ có 1 (thuật toán nhân ma trận đặc biệt)
  # → KHÔNG TÁCH, giữ nguyên
  ```
- **Don't / Bad Example (Optional):**
  ```python
  # SAI: Tách mù quáng chỉ vì 350 dòng
  # before: data_parser.py (350 dòng) - Chỉ 1 trách nhiệm: parse CSV đặc biệt
  # after: data_parser_part1.py (180 dòng) + data_parser_part2.py (170 dòng)
  # Kết quả: phải import cả 2 file, logic bị cắt ngang, khó đọc hơn
  ```
- **Scope (Optional):** Toàn bộ codebase.
- **Reference (Optional):** "A Philosophy of Software Design" - John Ousterhout (Chapter 4: Modules Should Be Deep)
- **Exceptions (Optional):** Không có ngoại lệ. Luôn phải phân tích trách nhiệm trước khi tách.
- **Terminal Command (Optional):** Không có lệnh tự động - yêu cầu AI Agent tự phân tích cấu trúc và trách nhiệm.
- **How to Test (Optional):**
  - Code review bắt buộc: Reviewer phải confirm file gốc có thực sự làm nhiều việc trước khi approve refactor.
  - Yêu cầu tác giả cung cấp danh sách trách nhiệm trước/sau khi tách.

---

## Tổng hợp các Standard dạng bảng

| Standard Name | Rule ID | Bắt buộc? | Công cụ kiểm tra tự động? |
|---|---|---|---|
| File Size & Single Responsibility | SRC-001 | ✅ Bắt buộc | Có (script đếm dòng) |
| No Circular Dependency | SRC-002 | ✅ Bắt buộc | Có (pylint, madge) |
| Preserve Public API & Behavior | SRC-003 | ✅ Bắt buộc | Có (so sánh test) |
| Cyclomatic Complexity <15 | SRC-004 | ✅ Bắt buộc | Có (radon, eslint) |
| Documentation & Type Hints | SRC-005 | ✅ Bắt buộc | Có (pydocstyle, mypy) |
| Branch by Abstraction | SRC-006 | ⚠️ Khuyến nghị (bắt buộc nếu file >500 dòng) | Không (cần review thủ công) |
| No Arbitrary Refactoring | SRC-007 | ✅ Bắt buộc | Không (cần phân tích logic) |
