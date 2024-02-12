selectWoo
=======
This fork of selectWoo contains additional accessibility and screenreader fixes, above those found in [woocommerce/selectWoo](https://github.com/woocommerce/selectWoo).

**Usage**:

[Usage is the same as select2](https://select2.github.io/examples.html), but can also be initialized with `.selectWoo()`. `.select2()` initialization has been kept for full backwards compatibility. If other versions of select2 are potentially going to be running on the same site, initializing elements with `.selectWoo()` is recommended.

You can enqueue the select2 or the selectWoo js and css files in the dist folder. They are the same.

## Additional features

In addition to the below, this fork of selectWoo contains various fixes to allow for a much improved screen reader experience.

### Label support

Unfortunately, select2 doesn't offer any way to assosiate a `label` element with a select2. However, you can get around this by adding `data-label="your label text"` to the original select element.

```
<label for="example-1">Pick your sauce</label>
<select class="select2" id="example-1" name="example-1" data-label="Pick your sauce">
    <option value="ketchup">Ketchup</option>
    <option value="hot">Hot</option>
    <option value="bbq">BBQ</option>
</select>
```

This will add a `aria-label` with your label text to the select2.

### Help/error text support

`aria-describedby` attributes and values are copied over to the select2 element.

## Screen reader support

Due to the complex aria patterns used in select2, screen reader experiences may vary. See the table below for an overview of behaviour for some common screen reader and browser combinations.

The following results are taken from the [testing playground page](https://github.com/jadu/selectWoo/blob/master/playground/index.html).

### Single select

Typical screen reader output:

* VO: "`{selected choice | placeholder}`, menu popup combo box, `{label}`, group, `{describedby}`"
* NVDA: "`{label}` grouping, `{selected choice | placeholder}` combobox collapsed, `{describedby}`"
* JAWS: "`{label}` `{selected choice | placeholder}` edit, combobox collapsed, `{describedby}`"

| Screen reader | OS     | Browser | Label read | Selection read | Options read | Describedby read |
|---------------|--------|---------|------------|----------------|--------------|------------------|
| Voiceover     | Mac OS | Safari  | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | Edge    | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | IE11    | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | Firefox | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | Chrome  | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 7  | IE11    | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 10 | Edge    | Yes        | Yes            | Yes          | No               |
| JAWS 2020     | Win 10 | IE11    | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 10 | Firefox | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 10 | Chrome  | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 7  | IE11    | Yes        | Yes            | Yes          | Yes              |

### Multi select

Typical screen reader output:

* VO: "`{label}`, edit text, `{selected choice | placeholder}`, `{describedby}`"
* NVDA: "`{label}` edit, has autocomplete, `{selected choice | placeholder}`, `{describedby}`"
* JAWS: "`{label}` edit, `{selected choice | placeholder}`, `{describedby}`"

| Screen reader | OS     | Browser | Label read | Selection read | Options read | Describedby read |
|---------------|--------|---------|------------|----------------|--------------|------------------|
| Voiceover     | Mac OS | Safari  | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | Edge    | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | IE11    | Yes        | Yes            | Yes          | No               |
| NVDA          | Win 10 | Firefox | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 10 | Chrome  | Yes        | Yes            | Yes          | Yes              |
| NVDA          | Win 7  | IE11    | Yes        | Yes            | Yes          | No               |
| JAWS 2020     | Win 10 | Edge    | Yes        | No             | Yes          | No               |
| JAWS 2020     | Win 10 | IE11    | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 10 | Firefox | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 10 | Chrome  | Yes        | Yes            | Yes          | Yes              |
| JAWS 2020     | Win 7  | IE11    | Yes        | Yes            | Yes          | Yes              |

## Known issues

* Voiceover reads the the selection twice, once before the label and once after. It's caused by VO reading the `aria-label` on the `span.select2-selection` combobox and the text value of `span.select2-selection__rendered` textbox. Currently there is no way to prevent this as both values are required for maximum screen reader support.

* IBM Equal Access Accessibility Checker reports a 4.1.2 Name, Role Value error relating to single selects having a `aria-expanded` value of `false` while the combobox popup is visible. This is due to the markup structure of single selects, where the parent "selection" controls the child "selection rendered" and the child is always visible (the selected option or placeholder). This appears to cause no issues in real world screen reader testing (see above tables).

