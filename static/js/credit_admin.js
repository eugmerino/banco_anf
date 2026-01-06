document.addEventListener("DOMContentLoaded", function() {
    // Selecciona los campos de garantía
    const guaranteeField = document.querySelector(".field-guarantee");
    const guarantorField = document.querySelector(".field-guarantee_fiador");

    // Función para mostrar/ocultar campos según tipo de garantía
    function toggleFields(value) {
        if (!value) value = "NONE";
        if (guaranteeField) guaranteeField.style.display = value === "GUARANTEE" ? "" : "none";
        if (guarantorField) guarantorField.style.display = value === "GUARANTOR" ? "" : "none";
    }

    const creditTypeSelect = $("#id_credit_type"); 

    if (!creditTypeSelect.length) return;

    // Inicial: mostrar/ocultar según el valor actual
    toggleFields(creditTypeSelect.find(":selected").data("guarantee-type"));

    // Detecta cambios tanto en Select normal como en Select2
    creditTypeSelect.on("change select2:select", function(e) {
        const guaranteeType = $(this).find(":selected").data("guarantee-type");
        console.log("Cambio detectado:", guaranteeType);
        toggleFields(guaranteeType);
    });
});

document.addEventListener("DOMContentLoaded", function () {

    const originalSelect = document.querySelector("#id_installment");

    if (!originalSelect) {
        console.log("No hay campo installment aquí");
        return;
    }

    $(originalSelect).on("select2:select", function (e) {
        const value = e.params.data.id;
        loadInstallmentData(value);
    });

    // Crear contenedor donde mostraremos la info
    const infoBox = document.createElement("div");
    infoBox.id = "installment-info";
    infoBox.style.marginTop = "10px";
    infoBox.style.padding = "10px";
    infoBox.style.border = "1px solid #ccc";
    infoBox.style.borderRadius = "5px";
    infoBox.style.display = "none";

    // Insertarlo debajo del contenedor visual de Select2
    const select2Container = originalSelect.closest(".form-row") ?? originalSelect.parentNode;
    select2Container.appendChild(infoBox);

    function loadInstallmentData(installmentId) {
        if (!installmentId) {
            infoBox.style.display = "none";
            return;
        }

        function formatDate(dateStr) {
            const [year, month, day] = dateStr.split("-");
            return `${day}/${month}/${year}`;
        }


        fetch(`/admin/credit/loanpayment/get-installment-data/${installmentId}/`)
            .then(response => response.json())
            .then(data => {
                infoBox.style.display = "block";
                infoBox.innerHTML = `
                    <strong>Detalle de la cuota</strong><br>
                    Capital: $${data.capital.toFixed(2)}<br>
                    Interés: $${data.interest.toFixed(2)}<br>
                    Mora: $${data.late_fees.toFixed(2)}<br>
                    <hr>
                    <strong>Total a pagar: $${data.total.toFixed(2)}</strong><br>
                    Fecha de vencimiento: ${formatDate(data.due_date)}
                `;
            })
            .catch(error => console.error("Error obteniendo los datos:", error));
    }

    // Si ya viene seleccionada (modo edición)
    if (originalSelect.value) {
        loadInstallmentData(originalSelect.value);
    }
});




