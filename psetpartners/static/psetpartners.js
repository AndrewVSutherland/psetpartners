var selectPureClassNames = {
    select: "select-pure__select",
    dropdownShown: "select-pure__select--opened",
    multiselect: "select-pure__select--multiple",
    label: "select-pure__label",
    placeholder: "select-pure__placeholder",
    dropdown: "select-pure__options",
    option: "select-pure__option",
    autocompleteInput: "select-pure__autocomplete",
    selectedLabel: "select-pure__selected-label",
    selectedOption: "select-pure__option--selected",
    placeholderHidden: "select-pure__placeholder--hidden",
    optionHidden: "select-pure__option--hidden",
};

function makeClassSelector(availableClasses, selectedClasses) {
    function class_selector_callback(value) {
        $('input[name="classes"]')[0].value = '[' + value + ']';
    }
    return new SelectPure("#institution_selector", {
        onChange: class_selector_callback,
        options: availableClasses,
        multiple: true,
        autocomplete: true,
        icon: "fa fa-times",
        inlineIcon: false,
        value: selectedClasses,
        classNames: selectPureClassNames,
    });
}


// disable drag and drop
function disable_drag() {
    document.addEventListener('drag', function(e) { e.preventDefault(); });
    document.addEventListener('drop', function(e) { e.preventDefault(); });
    document.addEventListener('dragstart', function(e) { e.preventDefault(); });
    document.addEventListener('dragend', function(e) { e.preventDefault(); });
    document.addEventListener('dragenter', function(e) { e.preventDefault(); });
    document.addEventListener('dragover', function(e) { e.preventDefault(); });
    document.addEventListener('dragleave', function(e) { e.preventDefault(); });
}

// must be called by any code using the checkboxgrid class
function setup_checkboxgrid(name,rows,cols) {
    disable_drag();
    $('span.checkboxgrid').on('mousedown mouseup mouseover', function a (e) {
        if ( typeof a.active === 'undefined' ) a.active = false;
        if ( e.type == 'mouseup' || (!(e.buttons&1) && e.type == 'mouseover') ) { a.active = false; return false; }
        if ( e.buttons&1 ) {
            var s = ('' + e.target.id).split('-'); 
            row = s[1]; col = s[2]; prefix = s[0];
            if ( e.type == 'mousedown' || (e.type == 'mouseover' && !a.active) ) {
                a.active = true;
                c = document.getElementById("check-" + e.target.id);
                a.mode = c.checked; a.row = row; a.col = col; a.prefix = prefix;
            }
            var srow = Math.min(a.row,row), erow = Math.max(a.row,row);
            var scol = Math.min(a.col,col); ecol = Math.max(a.col,col); 
            for ( var i = srow ; i <= erow ; i++ ) for ( var j = scol ; j <= ecol ; j++ ) {
                t = "check-" + a.prefix + "-" + i + "-" + j;
                c = document.getElementById(t);
                c.checked = !a.mode;
            }
            c.dispatchEvent(new Event('change'));
        }
        return false;
    });
    $('span.checkboxgrid').on('click', function (e) { e.preventDefault(); });
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
    var url = $('#'+id).val();
    if ( url == '' ) { $('#'+test_id).html(''); return; }
    if ( validURL(url) ) {
      $('#'+test_id).html('');
      if ( test_anchor != '') $('#'+test_id).html('<a href="' + url + '" target="_blank">' + test_anchor + '</a>');
    } else {
      $('#'+test_id).html(errmsg);
    }
}

function setup_url_tester(id, test_id, test_anchor, errmsg) {
  $('#'+id).keyup(function(evt) { evt.preventDefault(); url_tester(id, test_id, test_anchor, errmsg);});
  url_tester(id, test_id, test_anchor, errmsg);
}
