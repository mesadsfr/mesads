import Alpine from "alpinejs";

// This function must be called by the javascript page using formset_files.html
// to setup the directive "add-file-button".
export default function SetupFormsetFiles() {
  Alpine.directive("add-file-button", (el, { expression }, { evaluate }) => {
    el.addEventListener("click", () => {
      const form = document.getElementById("formset-files");
      if (!form) {
        throw new Error("formset-files not found");
      }

      // Initial number of forms in the formset
      const initialForms = Array.from(
        form.querySelectorAll("input[type=hidden]")
      ).find((form) => form.id.match(/INITIAL_FORMS/)) as HTMLInputElement;

      const numInitialForms = parseInt(initialForms.value, 10);

      // Retrieve the value of the "extra" x-data attribute
      const extra = evaluate("extra") as number;

      // For each file input (ie. for each new form), replace the string
      // __prefix__ present in formset.empty_form.file.id_for_label and
      // formset.empty_form.file.html_name by the form index. If the forms don't
      // have a correct index, the files will be ignored by django.
      el.parentElement
        ?.querySelectorAll("input[type=file]")
        .forEach((value) => {
          const input = value as HTMLInputElement;

          input.id = input.id.replace(
            /__prefix__/g,
            (extra + numInitialForms - 1).toString()
          );
          input.name = input.name.replace(
            /__prefix__/,
            (extra + numInitialForms - 1).toString()
          );
        });

      const totalInput = Array.from(
        form.querySelectorAll("input[type=hidden]")
      ).find((form) => form.id.match(/TOTAL_FORMS/)) as HTMLInputElement;

      const items = el.parentElement?.querySelectorAll("input[type=file]");

      if (items) {
        const last = items[items?.length - 1] as HTMLInputElement;
        last.focus();
      }

      totalInput.value = (parseInt(totalInput.value, 10) + 1).toString();
    });
  });
}
