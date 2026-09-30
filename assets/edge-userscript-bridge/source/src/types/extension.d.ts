// Own Message Types

import { ConfigKeys, ExtensionConfig } from '../background/config';
import { BackgroundToContent, ContentToBackground } from './communication';

export interface WebSocketConnectRequest {
    method: 'connectWebSocket';
    args?: {
        authorization: string;
        port: number;
    };
}

export interface MethodRequest {
    method: 'openOnlineEditor';
}

export interface NativeBridgeStateRequest {
    method: 'getNativeBridgeState';
}

export type ExtensionRequestMessage =
    | MethodRequest
    | NativeBridgeStateRequest
    | WebSocketConnectRequest
    | SetOptionRequest
    | GetOptionRequest
    | ContentToBackground;

export interface WebSocketConnectResponse {
    ok: boolean | null;
    error?: string;
}

export interface NativeBridgeStateResponse {
    state: 'unavailable' | 'connecting' | 'connected' | 'error';
}

export interface SetOptionRequest<T extends ConfigKeys = never> {
    method: 'setOption';
    args: { name: T; value: ExtensionConfig[T] };
}

export interface GetOptionRequest<T extends ConfigKeys = ConfigKeys> {
    method: 'getOption';
    args: { name: T; }
}

export interface GetOptionResponse<T extends ConfigKeys = ConfigKeys> {
    name: T;
    value: ExtensionConfig[T]
}

export type ExtensionResponseMessage =
    | WebSocketConnectResponse
    | NativeBridgeStateResponse
    | GetOptionResponse
    | BackgroundToContent;
