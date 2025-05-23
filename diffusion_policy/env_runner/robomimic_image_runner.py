import os
import wandb
import numpy as np
import torch
import collections
import pathlib
import tqdm
import h5py
import math
import dill
import copy
import wandb.sdk.data_types.video as wv
from diffusion_policy.gym_util.async_vector_env import AsyncVectorEnv
from diffusion_policy.gym_util.sync_vector_env import SyncVectorEnv
from diffusion_policy.gym_util.multistep_wrapper import MultiStepWrapper
from diffusion_policy.gym_util.video_recording_wrapper import VideoRecordingWrapper, VideoRecorder
from diffusion_policy.model.common.rotation_transformer import RotationTransformer

from diffusion_policy.policy.base_image_policy import BaseImagePolicy
from diffusion_policy.common.pytorch_util import dict_apply
from diffusion_policy.env_runner.base_image_runner import BaseImageRunner
from diffusion_policy.env.robomimic.robomimic_image_wrapper import RobomimicImageWrapper
import robomimic.utils.file_utils as FileUtils
import robomimic.utils.env_utils as EnvUtils
import robomimic.utils.obs_utils as ObsUtils

### Yilong
###########################################################################
# from action_extractor.action_identifier import ActionIdentifier, load_action_identifier

# robots = ['Panda', 'IIWA']
robots = ['IIWA']
###########################################################################


def create_env(env_meta, shape_meta, enable_render=True):
    modality_mapping = collections.defaultdict(list)
    for key, attr in shape_meta['obs'].items():
        modality_mapping[attr.get('type', 'low_dim')].append(key)
    ObsUtils.initialize_obs_modality_mapping_from_dict(modality_mapping)

    env = EnvUtils.create_env_from_metadata(
        env_meta=env_meta,
        render=False, 
        render_offscreen=enable_render,
        use_image_obs=enable_render, 
    )
    return env


class RobomimicImageRunner(BaseImageRunner):
    """
    Robomimic envs already enforces number of steps.
    """

    def __init__(self, 
            output_dir,
            dataset_path,
            shape_meta:dict,
            n_train=10,
            n_train_vis=3,
            train_start_idx=0,
            n_test=22,
            n_test_vis=6,
            test_start_seed=10000,
            max_steps=400,
            n_obs_steps=2,
            n_action_steps=8,
            render_obs_key='agentview_image',
            fps=10,
            crf=22,
            past_action=False,
            abs_action=False,
            tqdm_interval_sec=5.0,
            
            ### Yilong
            ###########################################################################
            #decoder_model_path=None,
            # encoder_model_path='/home/yilong/Documents/action_extractor/results/iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_resnet-53.pth',
            # decoder_model_path='/home/yilong/Documents/action_extractor/results/iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_mlp-53.pth',
            # conv_path = '/home/yilong/Documents/action_extractor/results/variational-iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_resnet-73.pth',
            # mlp_path = '/home/yilong/Documents/action_extractor/results/variational-iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_mlp-73.pth',
            # fc_mu_path = '/home/yilong/Documents/action_extractor/results/variational-iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_fc_mu-73.pth',
            # fc_logvar_path = '/home/yilong/Documents/action_extractor/results/variational-iiwa16168,lift1000-cropped_rgbd+color_mask-delta_position+gripper-frontside-cosine+mse-bs1632_fc_logvar-73.pth',

            ###########################################################################
            
            n_envs=None
        ):
        super().__init__(output_dir)

        if n_envs is None:
            n_envs = len(robots) * (n_train + n_test)

        # assert n_obs_steps <= n_action_steps
        dataset_path = os.path.expanduser(dataset_path)
        robosuite_fps = 20
        steps_per_render = max(robosuite_fps // fps, 1)

        # read from dataset
        env_meta = FileUtils.get_env_metadata_from_dataset(
            dataset_path)
        # disable object state observation
        env_meta['env_kwargs']['use_object_obs'] = False

        rotation_transformer = None
        if abs_action:
            env_meta['env_kwargs']['controller_configs']['control_delta'] = False
            rotation_transformer = RotationTransformer('axis_angle', 'rotation_6d')

        def make_env_fn(robot, render=True):
            def env_fn():
                # Work on a copy of env_meta so that changes here don't affect others.
                local_env_meta = copy.deepcopy(env_meta)
                local_env_meta['env_kwargs']['robots'] = [robot]  # Use a single robot
                robomimic_env = create_env(env_meta=local_env_meta, shape_meta=shape_meta, enable_render=render)
                # Disable hard reset for memory efficiency.
                robomimic_env.env.hard_reset = False
                return MultiStepWrapper(
                    VideoRecordingWrapper(
                        RobomimicImageWrapper(
                            env=robomimic_env,
                            shape_meta=shape_meta,
                            init_state=None,
                            render_obs_key=render_obs_key
                        ),
                        video_recoder=VideoRecorder.create_h264(
                            fps=fps,
                            codec='h264',
                            input_pix_fmt='rgb24',
                            crf=crf,
                            thread_type='FRAME',
                            thread_count=1
                        ),
                        file_path=None,
                        steps_per_render=steps_per_render
                    ),
                    n_obs_steps=n_obs_steps,
                    n_action_steps=n_action_steps,
                    max_episode_steps=max_steps
                )
            return env_fn

        def make_dummy_env_fn(robot):
            def dummy_env_fn():
                local_env_meta = copy.deepcopy(env_meta)
                local_env_meta['env_kwargs']['robots'] = [robot]
                robomimic_env = create_env(env_meta=local_env_meta, shape_meta=shape_meta, enable_render=False)
                return MultiStepWrapper(
                    VideoRecordingWrapper(
                        RobomimicImageWrapper(
                            env=robomimic_env,
                            shape_meta=shape_meta,
                            init_state=None,
                            render_obs_key=render_obs_key
                        ),
                        video_recoder=VideoRecorder.create_h264(
                            fps=fps,
                            codec='h264',
                            input_pix_fmt='rgb24',
                            crf=crf,
                            thread_type='FRAME',
                            thread_count=1
                        ),
                        file_path=None,
                        steps_per_render=steps_per_render
                    ),
                    n_obs_steps=n_obs_steps,
                    n_action_steps=n_action_steps,
                    max_episode_steps=max_steps
                )
            return dummy_env_fn

        env_fns = []
        for robot in robots:
            for _ in range(n_train + n_test):
                env_fns.append(make_env_fn(robot, render=True))
        env_seeds = list()
        env_prefixs = list()
        env_init_fn_dills = list()

        # train
        with h5py.File(dataset_path, 'r') as f:
            for robot in robots:
                for i in range(n_train):
                    train_idx = train_start_idx + i
                    enable_render = i < n_train_vis
                    init_state = f[f'data/demo_{train_idx}/states'][0]

                    def init_fn(env, init_state=init_state, enable_render=enable_render):
                        # setup rendering
                        assert isinstance(env.env, VideoRecordingWrapper)
                        env.env.video_recoder.stop()
                        env.env.file_path = None
                        if enable_render:
                            filename = pathlib.Path(output_dir).joinpath(
                                'media', wv.util.generate_id() + ".mp4")
                            filename.parent.mkdir(parents=False, exist_ok=True)
                            filename = str(filename)
                            env.env.file_path = filename

                        # assign the initial state
                        assert isinstance(env.env.env, RobomimicImageWrapper)
                        env.env.env.init_state = init_state

                    env_seeds.append(f"{robot}_train_{train_idx}")
                    env_prefixs.append(f'{robot}/train/')
                    env_init_fn_dills.append(dill.dumps(init_fn))
        
        # test
        for robot in robots:
            for i in range(n_test):
                seed = test_start_seed + i
                enable_render = i < n_test_vis

                def init_fn(env, seed=seed, enable_render=enable_render):
                    assert isinstance(env.env, VideoRecordingWrapper)
                    env.env.video_recoder.stop()
                    env.env.file_path = None
                    if enable_render:
                        filename = pathlib.Path(output_dir).joinpath(
                            'media', wv.util.generate_id() + ".mp4")
                        filename.parent.mkdir(parents=False, exist_ok=True)
                        filename = str(filename)
                        env.env.file_path = filename

                    # for test rollouts, reset using seed
                    assert isinstance(env.env.env, RobomimicImageWrapper)
                    env.env.env.init_state = None
                    env.seed(seed)

                env_seeds.append(f"{robot}_test_{seed}")
                env_prefixs.append(f'{robot}/test/')
                env_init_fn_dills.append(dill.dumps(init_fn))

        dummy_env_fn = make_dummy_env_fn(robots[0])
        env = AsyncVectorEnv(env_fns, dummy_env_fn=dummy_env_fn)
        # env = SyncVectorEnv(env_fns)

        self.env_meta = env_meta
        self.env = env
        self.env_fns = env_fns
        self.env_seeds = env_seeds
        self.env_prefixs = env_prefixs
        self.env_init_fn_dills = env_init_fn_dills
        self.fps = fps
        self.crf = crf
        self.n_obs_steps = n_obs_steps
        self.n_action_steps = n_action_steps
        self.past_action = past_action
        self.max_steps = max_steps
        self.rotation_transformer = rotation_transformer
        self.abs_action = abs_action
        self.tqdm_interval_sec = tqdm_interval_sec
        
        
        # Yilong
        ###########################################################################
        # self.encoder_model_path = encoder_model_path
        # self.decoder_model_path = decoder_model_path
        # self.conv_path = conv_path
        # self.mlp_path = mlp_path
        # self.fc_mu_path = fc_mu_path
        # self.fc_logvar_path = fc_logvar_path
        # if self.decoder_model_path != None:
        #     cameras=["frontview_image", "sideview_image"]
        #     stats_path='/home/yilong/Documents/ae_data/random_processing/iiwa16168/action_statistics_delta_position+gripper.npz'
        
        #     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
        #     self.action_identifier = load_action_identifier(
        #         conv_path=conv_path,
        #         mlp_path=mlp_path,
        #         fc_mu_path=fc_mu_path,
        #         fc_logvar_path=fc_logvar_path,
        #         resnet_version='resnet18',
        #         video_length=2,
        #         in_channels=len(cameras) * 6,  # Adjusted for multiple cameras
        #         action_length=1,
        #         num_classes=4,
        #         num_mlp_layers=3,
        #         stats_path=stats_path,
        #         coordinate_system='global',
        #         camera_name=cameras[0].split('_')[0]  # Use the first camera for initialization
        #     ).to(device)
        ###########################################################################

    def run(self, policy: BaseImagePolicy):
        device = policy.device
        dtype = policy.dtype
        env = self.env
        
        # plan for rollout
        n_envs = len(self.env_fns)
        n_inits = len(self.env_init_fn_dills)
        n_chunks = math.ceil(n_inits / n_envs)

        # allocate data
        all_video_paths = [None] * n_inits
        all_rewards = [None] * n_inits

        for chunk_idx in range(n_chunks):
            start = chunk_idx * n_envs
            end = min(n_inits, start + n_envs)
            this_global_slice = slice(start, end)
            this_n_active_envs = end - start
            this_local_slice = slice(0,this_n_active_envs)
            
            this_init_fns = self.env_init_fn_dills[this_global_slice]
            n_diff = n_envs - len(this_init_fns)
            if n_diff > 0:
                this_init_fns.extend([self.env_init_fn_dills[0]]*n_diff)
            assert len(this_init_fns) == n_envs

            # init envs
            env.call_each('run_dill_function', 
                args_list=[(x,) for x in this_init_fns])

            # start rollout
            obs = env.reset()
            past_action = None
            policy.reset()

            env_name = self.env_meta['env_name']
            pbar = tqdm.tqdm(total=self.max_steps, desc=f"Eval {env_name}Image {chunk_idx+1}/{n_chunks}", 
                leave=False, mininterval=self.tqdm_interval_sec)
            
            done = False
            while not done:
                # create obs dict
                np_obs_dict = dict(obs)
                if self.past_action and (past_action is not None):
                    # TODO: not tested
                    np_obs_dict['past_action'] = past_action[
                        :,-(self.n_obs_steps-1):].astype(np.float32)
                
                # device transfer
                obs_dict = dict_apply(np_obs_dict, 
                    lambda x: torch.from_numpy(x).to(
                        device=device))

                # run policy
                with torch.no_grad():
                    action_dict = policy.predict_action(obs_dict)
                    
                    # Yilong
                    ###########################################################################
                    # if self.decoder_model_path != None:
                    #     action_pred = action_dict['action_pred']
                        
                    #     batch_size, seq_len, feature_dim = action_pred.shape  # (28, 8, 512)

                    #     # Reshape to combine batch and sequence dimensions
                    #     flattened_input = action_pred.reshape(-1, feature_dim)  # (224, 512)

                    #     # Process with MLP
                    #     output = self.action_identifier.decode(flattened_input)  # (224, 4)

                    #     # Reshape back to (28, 8, 4)
                    #     output = output.view(batch_size, seq_len, -1)
                        
                    #     rotation_zeros = torch.zeros(output.shape[0], output.shape[1], 3).to(next(self.action_identifier.parameters()).device)

                    #     # Concatenate the tensors along the third axis
                    #     action_pred = torch.cat((output[:, :, :3] * 40, rotation_zeros, output[:, :, 3:]), dim=2)
                        
                    #     # norms = torch.norm(action_pred[:, :, :3], dim=2, keepdim=True)
                    #     # normalized_first_three = action_pred[:, :, :3] / norms

                    #     # Set the last component to -1 if negative and 1 if positive
                    #     last_component = torch.sign(action_pred[:, :, -1])

                    #     # Combine the normalized first three components, the middle three components, and the modified last component
                    #     action_pred = torch.cat((action_pred[:, :, :6], last_component.unsqueeze(2)), dim=2)
                        
                    #     action = action_pred[:,action_dict['start']:action_dict['end']]
                        
                    #     action_dict['action_pred'] = action_pred
                    #     action_dict['action'] = action
                        
                    #     del action_dict['start']
                    #     del action_dict['end']
                    ###########################################################################

                # device_transfer
                np_action_dict = dict_apply(action_dict,
                    lambda x: x.detach().to('cpu').numpy())

                action = np_action_dict['action']
                if not np.all(np.isfinite(action)):
                    print(action)
                    raise RuntimeError("Nan or Inf action")
                
                # step env
                env_action = action
                if self.abs_action:
                    env_action = self.undo_transform_action(action)

                obs, reward, done, info = env.step(env_action)
                done = np.all(done)
                past_action = action

                # update pbar
                pbar.update(action.shape[1])
            pbar.close()

            # collect data for this round
            all_video_paths[this_global_slice] = env.render()[this_local_slice]
            all_rewards[this_global_slice] = env.call('get_attr', 'reward')[this_local_slice]
        # clear out video buffer
        _ = env.reset()
        
        # log
        max_rewards = collections.defaultdict(list)
        log_data = dict()
        # results reported in the paper are generated using the commented out line below
        # which will only report and average metrics from first n_envs initial condition and seeds
        # fortunately this won't invalidate our conclusion since
        # 1. This bug only affects the variance of metrics, not their mean
        # 2. All baseline methods are evaluated using the same code
        # to completely reproduce reported numbers, uncomment this line:
        # for i in range(len(self.env_fns)):
        # and comment out this line
        for i in range(n_inits):
            seed = self.env_seeds[i]
            prefix = self.env_prefixs[i]
            max_reward = np.max(all_rewards[i])
            max_rewards[prefix].append(max_reward)
            log_data[prefix+f'sim_max_reward_{seed}'] = max_reward

            # visualize sim
            video_path = all_video_paths[i]
            if video_path is not None:
                sim_video = wandb.Video(video_path)
                log_data[prefix+f'sim_video_{seed}'] = sim_video
        
        # log aggregate metrics
        for prefix, value in max_rewards.items():
            name = prefix+'mean_score'
            value = np.mean(value)
            log_data[name] = value

        return log_data

    def undo_transform_action(self, action):
        raw_shape = action.shape
        if raw_shape[-1] == 20:
            # dual arm
            action = action.reshape(-1,2,10)

        d_rot = action.shape[-1] - 4
        pos = action[...,:3]
        rot = action[...,3:3+d_rot]
        gripper = action[...,[-1]]
        rot = self.rotation_transformer.inverse(rot)
        uaction = np.concatenate([
            pos, rot, gripper
        ], axis=-1)

        if raw_shape[-1] == 20:
            # dual arm
            uaction = uaction.reshape(*raw_shape[:-1], 14)

        return uaction
