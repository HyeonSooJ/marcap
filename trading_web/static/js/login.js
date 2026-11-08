document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = document.getElementById("loginErr");
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  err.hidden = true;
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: document.getElementById("pw").value }),
    });
    if (res.ok) { location.href = "/"; return; }
    const data = await res.json().catch(() => ({}));
    err.textContent = data.detail || "로그인 실패";
    err.hidden = false;
  } catch {
    err.textContent = "서버에 연결할 수 없습니다.";
    err.hidden = false;
  } finally {
    btn.disabled = false;
  }
});
