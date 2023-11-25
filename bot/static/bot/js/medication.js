function delete_lable() {
    label_form = document.querySelector("label[for='id_form']");
    label_units = document.querySelector("label[for='id_units']");
    label_form.remove();
    label_units.remove();
}

function required_form() {
    const form = document.getElementById('id_form');
    form.setAttribute('required', '');
}

function required_units() {
    const units = document.getElementById('id_units');
    units.setAttribute('required', '');
}

document.addEventListener('DOMContentLoaded', function() {
    delete_lable();
    const quantity = document.getElementById('id_quantity');
    const dosage = document.getElementById('id_dosage');
    quantity.addEventListener('input', required_form);
    dosage.addEventListener('input', required_units);
});


