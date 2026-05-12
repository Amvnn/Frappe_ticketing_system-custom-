<template>
  <SettingsLayoutBase
    :description="__('Configure Slack integration for ticket notifications and slash commands.')"
  >
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-semibold text-ink-gray-8">
          {{ __("Slack Integration") }}
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
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <span class="text-base font-medium text-ink-gray-8">
              {{ __("Enable Slack Integration") }}
            </span>
            <span class="text-p-sm text-ink-gray-6">
              {{ __("Post ticket notifications and accept slash commands via Slack.") }}
            </span>
          </div>
          <Switch
            v-model="form.enableSlackIntegration"
            :disabled="!canEdit"
          />
        </div>
        <hr />
        <div class="flex flex-col gap-4">
          <Password
            :label="__('Slack Bot Token')"
            v-model="form.slackBotToken"
            :placeholder="__('xoxb-...')"
            :disabled="!form.enableSlackIntegration || !canEdit"
            :readonly="!canEdit"
          />
          <Password
            :label="__('Slack Signing Secret')"
            v-model="form.slackSigningSecret"
            :placeholder="__('Signing secret from your Slack app')"
            :disabled="!form.enableSlackIntegration || !canEdit"
            :readonly="!canEdit"
          />
          <FormControl
            :label="__('Slack Notification Channel')"
            v-model="form.slackNotificationChannel"
            :placeholder="__('#devops-tickets')"
            :disabled="!form.enableSlackIntegration || !canEdit"
            :readonly="!canEdit"
          />
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

const auth = useAuthStore();

const canEdit = computed(() => auth.isAdmin || auth.isManager);

const form = reactive({
  enableSlackIntegration: false,
  slackBotToken: "",
  slackSigningSecret: "",
  slackNotificationChannel: "",
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
    form.enableSlackIntegration = Boolean(data.enable_slack_integration);
    form.slackBotToken = data.slack_bot_token || "";
    form.slackSigningSecret = data.slack_signing_secret || "";
    form.slackNotificationChannel = data.slack_notification_channel || "";
    initialData.value = JSON.stringify({ ...form });
  },
});

const saveResource = createResource({
  url: "frappe.client.set_value",
  makeParams() {
    return {
      doctype: "HD Settings",
      name: "HD Settings",
      fieldname: {
        enable_slack_integration: form.enableSlackIntegration ? 1 : 0,
        slack_bot_token: form.slackBotToken,
        slack_signing_secret: form.slackSigningSecret,
        slack_notification_channel: form.slackNotificationChannel,
      },
    };
  },
  onSuccess(data: any) {
    form.enableSlackIntegration = Boolean(data.enable_slack_integration);
    form.slackBotToken = data.slack_bot_token || "";
    form.slackSigningSecret = data.slack_signing_secret || "";
    form.slackNotificationChannel = data.slack_notification_channel || "";
    initialData.value = JSON.stringify({ ...form });
    toast.success(__("Slack settings saved"));
  },
  onError(err: any) {
    toast.error(err?.messages?.[0] || __("Failed to save Slack settings"));
  },
});

function saveSettings() {
  saveResource.submit();
}

watch(
  isDirty,
  (dirty) => {
    disableSettingModalOutsideClick.value = dirty;
  }
);
</script>
