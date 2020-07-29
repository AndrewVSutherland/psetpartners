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

function validURL(str) {
  var pattern = new RegExp('^https?:\\/\\/'+ // protocol (require)
    '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|'+ // domain name
    '((\\d{1,3}\\.){3}\\d{1,3}))'+ // OR ip (v4) address
    '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*'+ // port and path
    '(\\?[;&a-z\\d%_.~+=-]*)?'+ // query string
    '(\\#[-a-z\\d_]*)?$','i'); // fragment locator
  return !!pattern.test(str);
}

function url_tester(id, test_id, test_anchor, errmsg) {
    var url = $("#"+id).val();
    if ( url=="") { $("#"+test_id).html(""); return; }
    if ( validURL(url) ) {
      if ( test_anchor != "") $("#"+test_id).html("<a href='" + url + "' target='_blank'>" + test_anchor + "</a>");
    } else {
      $("#"+test_id).html(errmsg);
    }
}

function setup_url_tester(id, test_id, test_anchor, errmsg) {
  $("#"+id).keyup(function(evt) { evt.preventDefault(); url_tester(id, test_id, test_anchor, errmsg);});
  url_tester(id, test_id, test_anchor, errmsg);
}
