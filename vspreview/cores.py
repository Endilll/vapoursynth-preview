from vapoursynth import EnvironmentPolicy, EnvironmentPolicyAPI, register_policy
from vapoursynth EnvironmentData, Environment


__all__ = ("create_and_register_policy",)


class VSPreviewEnvironmentPolicy(object):
    __slots__ = ("_current_environment", "_api")
    _current_environment: EnvironmentData
    _api: EnvironmentPolicyAPI
        
    def reload_core(self):
        new_environment = self._api.create_environment()
        old_environment = self._current_environment
        self._current_environment = new_environment
        self._api.destroy_environment(old)

    def on_policy_registered(self, special_api: EnvironmentPolicyAPI):
        self._current_environment = special_api.create_environment()
        self._api = special_api

    def on_policy_cleared(self):
        pass

    def get_current_environment(self) -> EnvironmentData:
        return self._current_environment

    def set_environment(self, environment -> EnvironmentData):
        if environment != self._current_environment:
            raise ValueError("The passed environment is not valid.")
        
        
def create_and_register_policy() -> VSPreviewEnvironmentPolicy:
    policy = VSPreviewEnvironmentPolicy()
    register_policy(policy)
    return policy
