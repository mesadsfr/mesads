import Alpine from "alpinejs";
import SetupFormsetFiles from "./formset_files";

SetupFormsetFiles();

type DataType = {
  ads_creation_date: string;
  ads_in_use: string;
};

const data = JSON.parse(
  (document.getElementById("data") as HTMLScriptElement).text
) as DataType;

Alpine.data("get_x_data", () => ({
  ads_creation_date: data.ads_creation_date,

  get ads_before_2014() {
    const creation_date = new Date(this.ads_creation_date);
    if (creation_date < new Date("2014-10-01")) {
      return true;
    }
    return false;
  },

  // The field "attribution_date" should only be displayed for old ADS, or if the creation date is not set
  get should_display_attribution_date() {
    return !this.ads_creation_date || this.ads_before_2014;
  },

  ads_in_use: data.ads_in_use,

  extraADSUserForms: 0,
}));

Alpine.directive("add-ads-user-button", (el, { expression }, { evaluate }) => {
  el.addEventListener("click", () => {
    const form = document.getElementById("ads-users");
    if (!form) {
      throw new Error("ads-users div not found");
    }

    // For each entry, replace the string __prefix__ present in the id and name by the form index.
    el.parentElement
      ?.querySelectorAll(".fr-form-group")
      .forEach((value, index) => {
        const div = value as HTMLDivElement;

        const entries: NodeListOf<HTMLInputElement | HTMLSelectElement> =
          div.querySelectorAll("input, select");

        entries.forEach((value) => {
          value.id = value.id.replace(/__prefix__/g, index.toString());
          value.name = value.name.replace(/__prefix__/, index.toString());

          const label = value.parentNode?.querySelector(
            ":scope > label"
          ) as HTMLLabelElement;
          if (label) {
            label.htmlFor = value.id;
          }
        });
      });

    // Update the hidden field TOTAL_FORMS to let Django know how many forms to process
    const totalInput = Array.from(
      form.querySelectorAll("input[type=hidden]")
    ).find((form) => form.id.match(/TOTAL_FORMS/)) as HTMLInputElement;
    totalInput.value = (parseInt(totalInput.value, 10) + 1).toString();
  });
});

Alpine.start();
