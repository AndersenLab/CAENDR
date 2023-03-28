function toggle_input(id, val) {
  const el = document.getElementById(id);
  el.disabled     = !val;
  el.ariaDisabled = !val;
}
