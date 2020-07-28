// disable drag and drop
function disable_drag() {
    document.addEventListener("drag", function(e) { e.preventDefault(); });
    document.addEventListener("drop", function(e) { e.preventDefault(); });
    document.addEventListener("dragstart", function(e) { e.preventDefault(); });
    document.addEventListener("dragend", function(e) { e.preventDefault(); });
    document.addEventListener("dragenter", function(e) { e.preventDefault(); });
    document.addEventListener("dragover", function(e) { e.preventDefault(); });
    document.addEventListener("dragleave", function(e) { e.preventDefault(); });
}

// must be called by any code using the checkboxgrid class
function setup_checkboxgrid() {
    disable_drag();
    $("span.checkboxgrid").on("mousedown mouseover", function (e) {
    if (e.buttons & 1 ) {
        c = document.getElementById("check-" + e.target.id);
        c.checked = !c.checked;
    }
    });
    $("span.checkboxgrid").on("click", function (e) {e.preventDefault(); });
}
