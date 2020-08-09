const allowedAttributes = { value: "data-value", disabled: "data-disabled", class: "class", type: "type" };

class Element {
  constructor(element, attributes = {}, i18n = {}) {
    this._node = element instanceof HTMLElement ? element : document.createElement(element);
    this._config = { i18n };
    this._setAttributes(attributes);
    if (attributes.textContent) this._setTextContent(attributes.textContent);
    return this;
  }

  get() { return this._node; }
  append(element) { this._node.appendChild(element); return this; }
  addClass(className) { this._node.classList.add(className); return this; }
  removeClass(className) { this._node.classList.remove(className); return this; }
  toggleClass(className) { this._node.classList.toggle(className); return this; }
  addEventListener(type, callback) { this._node.addEventListener(type, callback); return this; }
  removeEventListener(type, callback) { this._node.removeEventListener(type, callback); return this; }
  setText(text) { this._setTextContent(text); return this; }
  getHeight() { return window.getComputedStyle(this._node).height; }
  setTop(top) { this._node.style.top = `${top}px`; return this; }
  focus() { this._node.focus(); return this; }
  _setTextContent(textContent) { this._node.textContent = textContent; }
  _setAttributes(attributes) {
    for (const key in attributes) {
      if (allowedAttributes[key] && attributes[key]) {
        this._setAttribute(allowedAttributes[key], attributes[key]);
      }
    }
  }
  _setAttribute(key, value) { this._node.setAttribute(key, value); }
}

const CLASSES = {
  select: "sp-select",                          // container div for select
  multiselect: "sp-multiselect",                // added to container div for multiselect
  selectOpen: "sp-select-open",                 // class added to container div when dropdown is open
  dropdown: "sp-dropdown",                      // container div for dropdown list
  label: "sp-label",                            // span showing selected option (or tags) in select div
  tag: "sp-tag",                                // span for tag correspdoning to a selected option in multiselect div
  placeholder: "sp-placeholder",                // span holding a place for label, can used to show open-arrow
  placeholderHidden: "sp-placeholder-hidden",   // class added to placeholder once an option is set
  option: "sp-option",                          // div for each option in dropdown list
  optionDisabled: "sp-option-disabled",         // class added to option when disabled
  optionHidden: "sp-option-hidden",             // class added to option when hidden
  optionSelected: "sp-option-selected",         // class added to option when selected
  autocompleteInput: "sp-autocomplete",         // text box for autocomplete input
};

class SelectPure {
  constructor(element, config) {
    this._config = { ...config, classNames: { ...CLASSES, ...config.classNames }, disabledOptions: [] };
    this._state = { opened: false };
    this._icons = [];
    this._boundHandleClick = this._handleClick.bind(this);
    this._boundUnselectOption = this._unselectOption.bind(this);
    this._boundSortOptions = this._sortOptions.bind(this);
    this._body = new Element(document.body);
    this._create(element);
    if ( this._config.value ) this._setValue();
  }

  // Public API
  value() { return this._config.value; }
  reset() { this._config.value = this._config.multiple ? [] : null; this._setValue(); }

  // Private methods
  _create(_element) {
    const element = typeof _element === "string" ? document.querySelector(_element) : _element;

    this._parent = new Element(element);
    this._select = new Element("div", { class: this._config.classNames.select });
    this._label = new Element("span", { class: this._config.classNames.label });
    this._optionsWrapper = new Element("div", { class: this._config.classNames.dropdown });
    if ( this._config.multiple ) this._select.addClass(this._config.classNames.multiselect);
    this._options = this._generateOptions();
    this._select.addEventListener("click", this._boundHandleClick);
    this._select.append(this._label.get());
    this._select.append(this._optionsWrapper.get());
    this._parent.append(this._select.get());
    this._placeholder = new Element("span", { class: this._config.classNames.placeholder, textContent: this._config.placeholder });
    this._select.append(this._placeholder.get());
  }

  _generateOptions() {
    if ( this._config.autocomplete ) {
      this._autocomplete = new Element("input", { class: this._config.classNames.autocompleteInput, type: "text" });
      this._autocomplete.addEventListener("input", this._boundSortOptions);
      this._optionsWrapper.append(this._autocomplete.get());
    }
    return this._config.options.map(_option => {
      const option = new Element("div", {
        class: `${this._config.classNames.option}${_option.disabled ?
          " " + this._config.classNames.optionDisabled : ""}`,
        value: _option.value,
        textContent: _option.label,
        disabled: _option.disabled,
      });
      if ( _option.disabled ) this._config.disabledOptions.push(String(_option.value));
      this._optionsWrapper.append(option.get());
      return option;
    });
  }

  _handleClick(event) {
    event.stopPropagation();

    if ( event.target.className === this._config.classNames.autocompleteInput ) return;

    if ( this._state.opened ) {
      const option = this._options.find(_option => _option.get() === event.target);
      if (option) {
        if ( option.get().classList.contains(this._config.classNames.optionSelected) ) {
          if ( this._config.multiple ) { this._unselectOption(event); return; }
        } else {
          this._setValue(option.get().getAttribute("data-value"), true);
          if ( this._config.multiple ) return;
        }
      }
      this._select.removeClass(this._config.classNames.selectOpen);
      this._body.removeEventListener("click", this._boundHandleClick);
      this._select.addEventListener("click", this._boundHandleClick);
      this._state.opened = false;
      return;
    }

    if ( event.target.className === this._config.icon ) return;

    this._select.addClass(this._config.classNames.selectOpen);
    this._body.addEventListener("click", this._boundHandleClick);
    this._select.removeEventListener("click", this._boundHandleClick);
    this._state.opened = true;
    if ( this._autocomplete ) this._autocomplete.focus();
  }

  _setValue(value, manual, unselected) {
    if ( this._config.disabledOptions.indexOf(value) > -1 ) return;
    if ( value && !unselected ) this._config.value = this._config.multiple ? [...this._config.value || [], value] : value;
    if ( value && unselected ) this._config.value = value;
    this._options.forEach(_option => { _option.removeClass(this._config.classNames.optionSelected); });
    this._placeholder.removeClass(this._config.classNames.placeholderHidden);

    if (this._config.multiple) {
      const options = this._config.value.map(_value => {
        const option = this._config.options.find(_option => _option.value === _value);
        const optionNode = this._options.find(_option => _option.get().getAttribute("data-value") === option.value.toString());
        optionNode.addClass(this._config.classNames.optionSelected);
        return option;
      });
      if ( options.length ) this._placeholder.addClass(this._config.classNames.placeholderHidden);
      this._selectOptions(options, manual);
      return;
    }

    const option = this._config.value ?
      this._config.options.find(_option => _option.value.toString() === this._config.value) :
      this._config.options[0];

    const optionNode = this._options.find (_option => _option.get().getAttribute("data-value") === option.value.toString());

    if (!this._config.value) { this._label.setText(""); return; }

    optionNode.addClass(this._config.classNames.optionSelected);
    this._placeholder.addClass(this._config.classNames.placeholderHidden);
    this._selectOption(option, manual);
  }

  _selectOption(option, manual) {
    this._selectedOption = option;
    this._label.setText(option.label);
    if ( this._config.onChange && manual ) this._config.onChange(option.value);
  }

  _selectOptions(options, manual) {
    this._label.setText("");
    this._icons = options.map(_option => {
      const tag = new Element("span", {
        class: this._config.classNames.tag,
        textContent:  this._config.shortlabels ? _option.value : _option.label,
      });
      const icon = new Element(this._config.inlineIcon ?
        this._config.inlineIcon.cloneNode(true) : "i", {
        class: this._config.icon,
        value: _option.value,
      });
      icon.addEventListener("click", this._boundUnselectOption);
      tag.append(icon.get());
      this._label.append(tag.get());
      return icon.get();
    });

    if (manual) this._optionsWrapper.setTop(Number(this._select.getHeight().split("px")[0]) + 5);
    if (this._config.onChange && manual) this._config.onChange(this._config.value);
  }

  _unselectOption(event) {
    const newValue = [...this._config.value];
    const index = newValue.indexOf(event.target.getAttribute("data-value"));
    if ( index !== -1 ) newValue.splice(index, 1);
    this._setValue(newValue, true, true);
    event.stopPropagation();
  }

  _sortOptions(event) {
    this._options.forEach(_option => {
      if (!_option.get().textContent.toLowerCase().includes(event.target.value.toLowerCase())) {
        _option.addClass(this._config.classNames.optionHidden);
        return;
      }
      _option.removeClass(this._config.classNames.optionHidden);
    });
  }
}
