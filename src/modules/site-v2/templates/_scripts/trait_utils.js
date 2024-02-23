// Render all provided components of the display name
function traitNameHTML(name_1, name_2, name_3) {
  let nameHTML;
  nameHTML = `<strong>${name_1}</strong>`;
  if (name_2) {
    nameHTML += `<p class="mb-0">${name_2}</p>`;
  }
  if (name_3) {
    if (!name_2) nameHTML += '<br />';
    nameHTML += `<em>${name_3}</em>`;
  }
  return nameHTML;
}
