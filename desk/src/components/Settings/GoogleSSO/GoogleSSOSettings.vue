<template>
  <SettingsLayoutBase
    :description="__('Configure Google SSO to allow users to sign in with their Google Workspace account.')"
  >
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-semibold text-ink-gray-8">
          {{ __("Google SSO") }}
        </h1>
        <Transition name="fade">
          <Badge
            v-if="isDirty"
            :label="__('Unsaved')"
            theme="orange"
            variant="subtle"
            size="sm"
          />
        </Transition>
      </div>
    </template>
    <template #header-actions>
      <Transition name="fade">
        <Button
          v-if="isDirty && canEdit"
          :label="__('Save')"
          variant="solid"
          @click="saveSettings"
          :loading="saveResource.loading"
        />
      </Transition>
    </template>
    <template #content>
      <div
        v-if="settingsResource.loading && !settingsResource.data"
        class="flex items-center justify-center mt-12"
      >
        <LoadingIndicator class="w-4" />
      </div>
      <div v-else class="flex flex-col gap-6 max-w-lg">
        <!-- Enable toggle -->
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <span class="text-base font-medium text-ink-gray-8">
              {{ __("Enable Google SSO") }}
            </span>
            <span class="text-p-sm text-ink-gray-6">
              {{ __("Allow users to sign in with their Google Workspace account.") }}
            </span>
          </div>
          <Switch
            v-model="form.enableGoogleSSO"
            :disabled="!canEdit"
          />
        </div>
        <hr />
        <div class="flex flex-col gap-4">
          <!-- Client ID -->
          <FormControl
            :label="__('Google Client ID')"
            v-model="form.googleClientId"
            :placeholder="__('your-client-id.apps.googleusercontent.com')"
            :disabled="!form.enableGoogleSSO || !canEdit"
            :readonly="!canEdit"
          />
          <!-- Client Secret -->
          <Password
            :label="__('Google Client Secret')"
            v-model="form.googleClientSecret"
            :placeholder="__('Client secret from Google Cloud Console')"
            :disabled="!form.enableGoogleSSO || !canEdit"
            :readonly="!canEdit"
          />
          <!-- Allowed Domains -->
          <div class="flex flex-col gap-2">
            <span
              class="text-sm font-medium"
              :class="!form.enableGoogleSSO || !canEdit ? 'text-ink-gray-4' : 'text-ink-gray-7'"
            >
              {{ __("Allowed Domains") }}
            </span>
            <p class="text-p-xs text-ink-gray-5">
              {{ __("Restrict login to these email domains. Leave empty to allow any Google account.") }}
            </p>
            <div class="flex flex-col gap-2">
              <div
                v-for="(domain, index) in form.allowedDomains"
                :key="index"
                class="flex items-center gap-2"
              >
                <FormControl
                  v-model="form.allowedDomains[index]"
                  :placeholder="__('company.com')"
                  :disabled="!form.enableGoogleSSO || !canEdit"
                  :readonly="!canEdit"
                  class="flex-1"
                />
                <Button
                  v-if="canEdit && form.enableGoogleSSO"
                  variant="ghost"
                  theme="red"
                  @click="removeDomain(index)"
                >
                  <template #icon>
                    <LucideX class="size-4" />
                  </template>
                </Button>
              </div>
              <Button
                v-if="canEdit && form.enableGoogleSSO"
                variant="subtle"
                :label="__('Add Domain')"
                @click="addDomain"
              >
                <template #prefix>
                  <LucidePlus class="size-4" />
                </template>
              </Button>
            </div>
          </div>
          <!-- Redirect URI (read-only) -->
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium text-ink-gray-7">
              {{ __("Redirect URI") }}
            </span>
            <p class="text-p-xs text-ink-gray-5">
              {{ __("Register this URI in your Google Cloud Console OAuth2 credentials.") }}
            </p>
            <div class="flex items-center gap-2">
              <FormControl
                :value="redirectUri"
                readonly
                class="flex-1 font-mono text-xs"
              />
              <Button
                variant="subtle"
                :label="__('Copy')"
                @click="copyRedirectUri"
              >
                <template #prefix>
                  <LucideCopy class="size-4" />
                </template>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup lang="ts">
import { Badge, Button, createResource, FormControl, LoadingIndicator, Switch, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import { __ } from "@/translation";
import { useAuthStore } from "@/stores/auth";
import { disableSettingModalOutsideClick } from "../settingsModal";
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import Password from "@/components/Password.vue";
import LucidePlus from "~icons/lucide/plus";
import LucideX from "~icons/lucide/x";
import LucideCopy from "~icons/lucide/copy";

const auth = useAuthStore();

const canEdit = computed(() => auth.isAdmin || auth.isManager);

const redirectUri = computed(
  () => `${window.location.origin}/api/method/helpdesk.api.google_sso.handle_google_callback`
);

const form = reactive({
  enableGoogleSSO: false,
  googleClientId: "",
  googleClientSecret: "",
  allowedDomains: [] as string[],
});

const initialData = ref<string | null>(null);
const isDirty = computed(() => {
  if (!initialData.value) return false;
  return JSON.stringify(form) !== initialData.value;
});

const settingsResource = createResource({
  url: "frappe.client.get",
  params: {
    doctype: "HD Settings",
    name: "HD Settings",
  },
  auto: true,
  onSuccess(data: any) {
    form.enableGoogleSSO = Boolean(data.enable_google_sso);
    form.googleClientId = data.google_client_id || "";
    form.googleClientSecret = data.google_client_secret || "";
    form.allowedDomains = (data.google_sso_allowed_domains || []).map(
      (row: any) => row.domain || ""
    );
    initialData.value = JSON.stringify({ ...form, allowedDomains: [...form.allowedDomains] });
  },
});

const saveResource = createResource({
  url: "frappe.client.set_value",
  makeParams() {
    return {
      doctype: "HD Settings",
      name: "HD Settings",
      fieldname: {
        enable_google_sso: form.enableGoogleSSO ? 1 : 0,
        google_client_id: form.googleClientId,
        google_client_secret: form.googleClientSecret,
        google_sso_allowed_domains: form.allowedDomains
          .filter((d) => d.trim() !== "")
          .map((domain) => ({ domain })),
      },
    };
  },
  onSuccess(data: any) {
    form.enableGoogleSSO = Boolean(data.enable_google_sso);
    form.googleClientId = data.google_client_id || "";
    form.googleClientSecret = data.google_client_secret || "";
    form.allowedDomains = (data.google_sso_allowed_domains || []).map(
      (row: any) => row.domain || ""
    );
    initialData.value = JSON.stringify({ ...form, allowedDomains: [...form.allowedDomains] });
    toast.success(__("Google SSO settings saved"));
  },
  onError(err: any) {
    toast.error(err?.messages?.[0] || __("Failed to save Google SSO settings"));
  },
});

function saveSettings() {
  saveResource.submit();
}

function addDomain() {
  form.allowedDomains.push("");
}

function removeDomain(index: number) {
  form.allowedDomains.splice(index, 1);
}

async function copyRedirectUri() {
  try {
    await navigator.clipboard.writeText(redirectUri.value);
    toast.success(__("Redirect URI copied to clipboard"));
  } catch {
    toast.error(__("Failed to copy to clipboard"));
  }
}

watch(isDirty, (dirty) => {
  disableSettingModalOutsideClick.value = dirty;
});
</script>
