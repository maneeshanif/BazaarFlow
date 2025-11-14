"use client";

import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import axios from "axios";
import { Loader2, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { useSalesVendor } from "@/components/sales/VendorContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface VendorResponse {
  vendor_id: string;
  phone_number_id: string;
}

interface VendorSettingsResponse {
  vendor_id: string;
  phone_number_id: string | null;
  waba_id: string | null;
  has_access_token: boolean;
  access_token_suffix: string | null;
}

interface FormState {
  phoneNumberId: string;
  wabaId: string;
  accessToken: string;
}

const createEmptyForm = (): FormState => ({
  phoneNumberId: "",
  wabaId: "",
  accessToken: "",
});

export default function SalesSettingsForm() {
  const { vendorId, setVendorId } = useSalesVendor();

  const [formState, setFormState] = useState<FormState>(createEmptyForm);
  const [loadingSettings, setLoadingSettings] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [hasStoredToken, setHasStoredToken] = useState<boolean>(false);
  const [storedTokenSuffix, setStoredTokenSuffix] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const loadSettings = useCallback(
    async (id: string | null) => {
      if (!id) {
        setFormState(createEmptyForm());
        setHasStoredToken(false);
        setStoredTokenSuffix(null);
        setFormError(null);
        setLoadingSettings(false);
        return;
      }

      try {
        setLoadingSettings(true);
        setFormError(null);
        const { data } = await axios.get<VendorSettingsResponse>(`${API_BASE}/api/vendors/${id}/settings`);
        setFormState({
          phoneNumberId: data.phone_number_id ?? "",
          wabaId: data.waba_id ?? "",
          accessToken: "",
        });
        setHasStoredToken(data.has_access_token);
        setStoredTokenSuffix(data.access_token_suffix ?? null);
      } catch (error) {
        const message = axios.isAxiosError(error)
          ? error.response?.data?.detail ?? error.message
          : "Unexpected error while loading settings.";
        setFormError(message);
        toast.error("Unable to load settings", { description: message });
      } finally {
        setLoadingSettings(false);
      }
    },
    [],
  );

  useEffect(() => {
    setLoadingSettings(true);
    loadSettings(vendorId || null);
  }, [vendorId, loadSettings]);

  const updateField = (field: keyof FormState) => (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const value = event.target.value;
    setFormState((previous) => ({ ...previous, [field]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const phoneNumberId = formState.phoneNumberId.trim();
    const wabaId = formState.wabaId.trim();
    const accessToken = formState.accessToken.trim();

    if (!phoneNumberId || !wabaId || !accessToken) {
      const message = "Phone Number ID, WhatsApp Business Account ID, and Access Token are required.";
      setFormError(message);
      toast.error("Missing required fields", {
        description: "Provide the phone number ID, WhatsApp Business ID, and access token to continue.",
      });
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      let activeVendorId = vendorId;

      if (!activeVendorId) {
        const createPayload = { phone_number_id: phoneNumberId, name: phoneNumberId };
        const { data: created } = await axios.post<VendorResponse>(`${API_BASE}/api/vendors`, createPayload);
        activeVendorId = created.vendor_id;
        setVendorId(created.vendor_id);
        toast.success("Vendor profile created", {
          description: `Vendor ${created.vendor_id} is now active.`,
        });
      }

      if (!activeVendorId) {
        throw new Error("Unable to resolve vendor ID after creation.");
      }

      const payload = {
        phone_number_id: phoneNumberId,
        waba_id: wabaId,
        access_token: accessToken,
      };

      const { data } = await axios.post<VendorSettingsResponse>(
        `${API_BASE}/api/vendors/${activeVendorId}/settings`,
        payload,
      );

      setHasStoredToken(data.has_access_token);
      setStoredTokenSuffix(data.access_token_suffix ?? null);
      setFormState((previous) => ({ ...previous, accessToken: "" }));

      toast.success("WhatsApp credentials saved", {
        description: "Meta validation succeeded and the credentials were stored securely.",
      });

      await loadSettings(activeVendorId);
    } catch (error) {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail ?? error.message
        : "Unexpected error while saving credentials.";
      setFormError(message);
      toast.error("Unable to save credentials", { description: message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleClearVendor = async () => {
    setVendorId("");
    await loadSettings(null);
  };

  return (
    <Card className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#174143]">WhatsApp Cloud API</p>
          <h2 className="text-2xl font-semibold text-slate-900">Connect Meta Credentials</h2>
          <p className="text-sm text-slate-600">
            Provide your Phone Number ID, WhatsApp Business Account ID, and a valid access token. We confirm the details with Meta before
            saving.
          </p>
          {!vendorId && (
            <p className="text-xs text-slate-500">
              No vendor selected yet—saving the form will create one automatically using the phone number ID.
            </p>
          )}
        </div>
        <Sparkles className="hidden h-8 w-8 text-[#174143] sm:block" />
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="grid gap-4">
          <div className="space-y-2">
            <Label htmlFor="phone-number-id">Phone Number ID</Label>
            <Input
              id="phone-number-id"
              value={formState.phoneNumberId}
              onChange={updateField("phoneNumberId")}
              placeholder="123456789012345"
              required
              disabled={loadingSettings || submitting}
            />
            <p className="text-xs text-slate-500">Capture this from WhatsApp Manager → API Setup in Meta Business Manager.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="waba-id">WhatsApp Business Account ID</Label>
            <Input
              id="waba-id"
              value={formState.wabaId}
              onChange={updateField("wabaId")}
              placeholder="987654321098765"
              required
              disabled={loadingSettings || submitting}
            />
            <p className="text-xs text-slate-500">Also known as the WABA ID. You&apos;ll find it beside the phone number configuration.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="access-token">Access Token</Label>
            <Textarea
              id="access-token"
              value={formState.accessToken}
              onChange={updateField("accessToken")}
              placeholder="EAAG..."
              required
              disabled={submitting}
              rows={3}
            />
            <p className="text-xs text-slate-500">
              Paste a long-lived system user token with WhatsApp Business Messaging permissions.
            </p>
            {hasStoredToken && storedTokenSuffix && (
              <p className="text-xs text-[#174143]">Stored token ending with {storedTokenSuffix}</p>
            )}
          </div>
        </div>

        {formError && <p className="text-sm text-red-500">{formError}</p>}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={submitting} className="bg-[#174143] text-white hover:bg-[#174143]/90">
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Save Credentials
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={handleClearVendor}
            disabled={loadingSettings || submitting || !vendorId}
          >
            Clear Selection
          </Button>
          {loadingSettings && (
            <div className="flex items-center text-sm text-slate-500">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading settings…
            </div>
          )}
          {vendorId && !loadingSettings && (
            <div className="text-sm text-slate-500">Active vendor ID: {vendorId}</div>
          )}
        </div>
      </form>
    </Card>
  );
}
